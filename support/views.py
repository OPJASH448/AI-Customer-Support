from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser


from .models import Document, DocumentChunk, Conversation, Message, EscalationTicket
from .serializers import (
    DocumentSerializer,
    DocumentUploadSerializer,
    DocumentChunkSerializer,
    ConversationSerializer,
    MessageSerializer,
    EscalationTicketSerializer
)
from .tasks import process_document


class DocumentViewSet(viewsets.ModelViewSet):
    """Document management endpoints"""
    permission_classes = [IsAuthenticated]
    serializer_class = DocumentSerializer
    parser_classes = (MultiPartParser, FormParser)

    def get_queryset(self):
        return Document.objects.filter(uploaded_by=self.request.user)

    def get_serializer_class(self):
        if self.action == 'create':
            return DocumentUploadSerializer
        return DocumentSerializer

    def create(self, request, *args, **kwargs):
        """Upload a document (PDF or TXT)"""
        # Ensure multipart/form-data was used and file is present
        file_obj = None
        if 'file' in request.FILES:
            file_obj = request.FILES.get('file')

        # Combine data and files into a mutable dict for the serializer
        data = request.data.copy()
        if file_obj is not None:
            data['file'] = file_obj

        serializer = self.get_serializer(data=data)
        if serializer.is_valid():
            # Create document and attach file
            document = serializer.save(uploaded_by=request.user, status='processing')

            # Process document synchronously so it always completes,
            # even when no Celery worker is running.
            task_status_message = 'Document uploaded and processed successfully.'
            try:
                result = process_document(document.id)
                if isinstance(result, dict) and result.get('status') == 'failed':
                    task_status_message = (
                        f"Document uploaded, but processing failed: "
                        f"{result.get('error', 'unknown error')}"
                    )
            except Exception as proc_err:
                task_status_message = (
                    f'Document uploaded, but processing failed: {str(proc_err)}'
                )

            # Reload document from DB to reflect post-processing state
            document.refresh_from_db()

            return Response(
                {
                    'message': task_status_message,
                    'document': DocumentSerializer(document).data
                },
                status=status.HTTP_201_CREATED
            )

        # Return clearer error when file missing or wrong encoding
        errors = serializer.errors
        if not file_obj and ('file' in errors or not str(request.content_type).startswith('multipart')):
            errors['file'] = errors.get('file', []) + [
                'No file was uploaded. Use multipart/form-data with a form field named "file".'
            ]
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def chunks(self, request, pk=None):
        """Get all chunks for a document"""
        document = self.get_object()
        chunks = document.chunks.all()
        serializer = DocumentChunkSerializer(chunks, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """Get document processing status"""
        document = self.get_object()
        return Response({
            'id': document.id,
            'title': document.title,
            'status': document.status,
            'chunk_count': document.chunks.count(),
            'created_at': document.created_at,
            'updated_at': document.updated_at
        })


class ConversationViewSet(viewsets.ModelViewSet):
    """Conversation endpoints"""
    permission_classes = [IsAuthenticated]
    serializer_class = ConversationSerializer

    def get_queryset(self):
        return Conversation.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """Get all messages in a conversation"""
        conversation = self.get_object()
        messages = conversation.messages.all()
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)


class MessageViewSet(viewsets.ModelViewSet):
    """Message endpoints"""
    permission_classes = [IsAuthenticated]
    serializer_class = MessageSerializer

    def get_queryset(self):
        return Message.objects.filter(conversation__user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EscalationTicketViewSet(viewsets.ModelViewSet):
    """Escalation ticket endpoints"""
    permission_classes = [IsAuthenticated]
    serializer_class = EscalationTicketSerializer

    def get_queryset(self):
        return EscalationTicket.objects.all()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

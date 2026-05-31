from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from django.db.models import Avg, Count, Q, F
from django.utils import timezone


from .models import Document, DocumentChunk, Conversation, Message, EscalationTicket
from .serializers import (
    DocumentSerializer,
    DocumentUploadSerializer,
    DocumentChunkSerializer,
    ConversationSerializer,
    MessageSerializer,
    EscalationTicketSerializer,
    TicketListSerializer,
    TicketResolveSerializer,
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


# ─── NEW: Ticket Queue API ───────────────────────────────────────────────────

class TicketListView(generics.ListAPIView):
    """
    GET /api/tickets/
    Priority queue: tickets ordered by priority descending (critical > high > medium > low).
    Supports ?status=open filter.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = TicketListSerializer

    # Map priority labels to numeric sort values (higher = more urgent)
    PRIORITY_ORDER = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}

    def get_queryset(self):
        qs = EscalationTicket.objects.select_related('conversation', 'assigned_to')

        # Filter by status if provided
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

        # Filter by priority if provided
        priority_filter = self.request.query_params.get('priority')
        if priority_filter:
            qs = qs.filter(priority=priority_filter)

        # Order by priority descending using a CASE expression
        from django.db.models import Case, When, IntegerField
        priority_ordering = Case(
            When(priority='critical', then=4),
            When(priority='high', then=3),
            When(priority='medium', then=2),
            When(priority='low', then=1),
            output_field=IntegerField(),
        )
        return qs.annotate(priority_rank=priority_ordering).order_by('-priority_rank', '-created_at')


class TicketResolveView(generics.UpdateAPIView):
    """
    PATCH /api/tickets/<id>/resolve/
    Resolve a ticket: sets status='resolved', saves agent_reply, records resolved_at.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = TicketResolveSerializer
    queryset = EscalationTicket.objects.all()
    http_method_names = ['patch']


class AnalyticsView(APIView):
    """
    GET /api/analytics/
    Returns aggregate support metrics:
      - total_conversations
      - escalation_rate (%)
      - avg_resolution_time_minutes
      - open_tickets
      - top_unanswered (top 5 unresolved ticket topics)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        total_conversations = Conversation.objects.count()
        total_tickets = EscalationTicket.objects.count()

        # Escalation rate = tickets / conversations * 100
        escalation_rate = 0.0
        if total_conversations > 0:
            escalation_rate = round((total_tickets / total_conversations) * 100, 2)

        # Average resolution time (only resolved tickets with resolved_at set)
        resolved_tickets = EscalationTicket.objects.filter(
            status='resolved',
            resolved_at__isnull=False,
        )
        avg_resolution = None
        if resolved_tickets.exists():
            # Calculate average of (resolved_at - created_at) in seconds, convert to minutes
            from django.db.models import ExpressionWrapper, DurationField
            durations = resolved_tickets.annotate(
                resolution_duration=ExpressionWrapper(
                    F('resolved_at') - F('created_at'),
                    output_field=DurationField()
                )
            )
            avg_duration = durations.aggregate(avg=Avg('resolution_duration'))['avg']
            if avg_duration:
                avg_resolution = round(avg_duration.total_seconds() / 60, 2)

        # Open tickets count
        open_tickets = EscalationTicket.objects.filter(
            status__in=['open', 'in_progress']
        ).count()

        # Top 5 unanswered topics — extract from unresolved ticket issues
        unresolved = EscalationTicket.objects.filter(
            status__in=['open', 'in_progress']
        ).order_by('-created_at')[:5]
        top_unanswered = [ticket.issue[:200] for ticket in unresolved]

        return Response({
            'total_conversations': total_conversations,
            'escalation_rate': escalation_rate,
            'avg_resolution_time_minutes': avg_resolution,
            'open_tickets': open_tickets,
            'top_unanswered': top_unanswered,
        })

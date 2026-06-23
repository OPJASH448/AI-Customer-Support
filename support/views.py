from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from django.db.models import Avg, Count, Q, F
from django.utils import timezone
import logging
import threading
import os

logger = logging.getLogger(__name__)

# Use Celery ONLY when explicitly enabled via env var (requires a running worker).
# Default is False — processing runs in a daemon thread inside the web process.
# To enable Celery: set USE_CELERY=true in your environment / Render dashboard.
_USE_CELERY = os.environ.get('USE_CELERY', 'false').strip().lower() == 'true'



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
    RAGAskSerializer,
)
from .tasks import process_document
from .rag import hybrid_retrieve, generate_grounded_answer


def _dispatch_thread(doc_id):
    """
    Run process_document() in a background daemon thread.

    This is the default processing path when USE_CELERY=false (or not set).
    It calls the exact same Celery task function directly — no broker needed.
    The DB connection opened by the thread is closed when the thread finishes
    to prevent connection pool leaks in long-running gunicorn processes.
    """
    from django.db import connection

    def _run(document_id):
        try:
            logger.info("process_document[%s] thread started.", document_id)
            process_document(document_id)
            logger.info("process_document[%s] thread completed.", document_id)
        except Exception as exc:
            logger.error(
                "process_document[%s] thread failed: %s",
                document_id, exc,
            )
        finally:
            connection.close()   # release DB connection back to pool

    thread = threading.Thread(
        target=_run,
        args=(doc_id,),
        daemon=True,
        name=f"doc-process-{doc_id}",
    )
    thread.start()
    logger.info(
        "process_document[%s] dispatched to thread (thread=%s).",
        doc_id, thread.name,
    )




class DocumentViewSet(viewsets.ModelViewSet):
    """Document management endpoints"""
    permission_classes = [IsAuthenticated]
    throttle_classes = []
    serializer_class = DocumentSerializer
    parser_classes = (MultiPartParser, FormParser)

    def get_queryset(self):
        return Document.objects.filter(uploaded_by=self.request.user)

    def get_serializer_class(self):
        if self.action == 'create':
            return DocumentUploadSerializer
        return DocumentSerializer

    def create(self, request, *args, **kwargs):
        """
        Upload a document (PDF or TXT).

        Processing strategy (controlled by USE_CELERY env var):

          USE_CELERY=true  → dispatch to Celery worker via Redis broker.
                             Requires a running Celery worker process.

          USE_CELERY=false → run process_document() inside a daemon thread
          (default)          directly in the web process. Works on any host
                             without a separate worker service.

        HTTP 201 is returned immediately in both cases.
        """
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            document = serializer.save(uploaded_by=request.user, status='processing')
            doc_id = document.id

            if _USE_CELERY:
                # ── Celery path (USE_CELERY=true) ─────────────────────────────
                # Only use this when a Celery worker is actually running.
                try:
                    result = process_document.apply_async(
                        args=(doc_id,),
                        expires=600,
                    )
                    logger.info(
                        "process_document[%s] queued via Celery (task_id=%s).",
                        doc_id, result.id,
                    )
                except Exception as exc:
                    # Celery enqueue failed — fall through to thread as safety net
                    logger.error(
                        "process_document[%s] Celery enqueue failed (%s). "
                        "Falling back to thread.",
                        doc_id, exc,
                    )
                    _dispatch_thread(doc_id)
            else:
                # ── Thread path (default, USE_CELERY=false) ───────────────────
                # Runs the same process_document() task function directly
                # in a background daemon thread — no worker process needed.
                _dispatch_thread(doc_id)

            return Response(
                {
                    'message': 'Document uploaded. Processing started — refresh in a few seconds.',
                    'document': DocumentSerializer(document).data,
                    'async': True,
                    'celery_enabled': _USE_CELERY,
                },
                status=status.HTTP_201_CREATED,
            )

        # Return clearer error when file missing or wrong encoding
        errors = serializer.errors
        if 'file' not in request.FILES and not str(request.content_type).startswith('multipart'):
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
        """Get document processing status with chunk progress."""
        document = self.get_object()
        chunk_count = document.chunks.count()
        return Response({
            'id': document.id,
            'title': document.title,
            'status': document.status,
            'chunk_count': chunk_count,
            'is_ready': document.status == 'ready',
            'original_filename': document.original_filename,
            'file_url': document.file_url,
            'created_at': document.created_at,
            'updated_at': document.updated_at,
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


# ─── Ticket Queue API ────────────────────────────────────────────────────────

class TicketListView(generics.ListAPIView):
    """
    GET /api/tickets/
    Priority queue: tickets ordered by priority descending (critical > high > medium > low).
    Supports ?status=open filter.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = []
    serializer_class = TicketListSerializer

    PRIORITY_ORDER = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}

    def get_queryset(self):
        qs = EscalationTicket.objects.select_related('conversation', 'assigned_to')

        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

        priority_filter = self.request.query_params.get('priority')
        if priority_filter:
            qs = qs.filter(priority=priority_filter)

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
    throttle_classes = []
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
    throttle_classes = []

    def get(self, request):
        total_conversations = Conversation.objects.count()
        total_tickets = EscalationTicket.objects.count()

        escalation_rate = 0.0
        if total_conversations > 0:
            escalation_rate = round((total_tickets / total_conversations) * 100, 2)

        resolved_tickets = EscalationTicket.objects.filter(
            status='resolved',
            resolved_at__isnull=False,
        )
        avg_resolution = None
        if resolved_tickets.exists():
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

        open_tickets = EscalationTicket.objects.filter(
            status__in=['open', 'in_progress']
        ).count()

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


class RAGAskView(APIView):
    """
    POST /api/support/rag/ask/
    Hybrid RAG flow:
      1) Dense retrieval  — pgvector HNSW cosine similarity (Gemini 768-dim embeddings)
      2) Sparse retrieval — BM25 keyword search (rank_bm25, in-memory)
      3) RRF fusion       — Reciprocal Rank Fusion (k=60) to merge ranked lists
      4) Generate grounded answer from top-k fused chunks via Gemini 2.0 Flash
      5) Persist user/assistant messages and linked context chunks
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = RAGAskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        question = serializer.validated_data['question']
        top_k = serializer.validated_data.get('top_k', 5)
        conversation_id = serializer.validated_data.get('conversation_id')

        # Resolve or create conversation
        if conversation_id:
            conversation = Conversation.objects.filter(
                id=conversation_id,
                user=request.user,
            ).first()
            if not conversation:
                return Response(
                    {'detail': 'Conversation not found for this user.'},
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            conversation = Conversation.objects.create(
                user=request.user,
                title=question[:80],
            )

        # Persist user message
        Message.objects.create(
            conversation=conversation,
            role='user',
            content=question,
            tokens_used=0,
        )

        # ── Hybrid RAG: dense + BM25 + RRF fusion ─────────────────────────────
        try:
            chunks = hybrid_retrieve(
                question=question,
                user=request.user,
                top_k=top_k,
            )
            answer = generate_grounded_answer(question, chunks)
        except Exception as e:
            error_str = str(e)
            if 'quota' in error_str.lower() or '429' in error_str:
                return Response(
                    {'error': 'Gemini API Rate Limit Exceeded. Please try again in a few seconds.'},
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )
            return Response(
                {'error': f'Hybrid RAG failed: {error_str}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Persist assistant answer and link context chunks
        assistant_msg = Message.objects.create(
            conversation=conversation,
            role='assistant',
            content=answer,
            tokens_used=0,
        )
        if chunks:
            assistant_msg.context_chunks.set(chunks)

        sources = [
            {
                'document_id': chunk.document_id,
                'document_title': chunk.document.title,
                'chunk_id': chunk.id,
                'chunk_index': chunk.chunk_index,
            }
            for chunk in chunks
        ]

        return Response(
            {
                'conversation_id': conversation.id,
                'question': question,
                'answer': answer,
                'sources': sources,
                'retrieval_method': 'hybrid',
                'retrieval_breakdown': {
                    'retrievers': ['dense_pgvector_hnsw', 'sparse_bm25'],
                    'fusion': 'reciprocal_rank_fusion',
                    'final_chunks': len(chunks),
                },
            },
            status=status.HTTP_200_OK,
        )

from rest_framework import serializers
from django.conf import settings
from .models import Document, DocumentChunk, Conversation, Message, EscalationTicket
import uuid
import logging

logger = logging.getLogger(__name__)


class DocumentChunkSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentChunk
        fields = ['id', 'document', 'content', 'chunk_index', 'tokens', 'created_at']
        read_only_fields = ['id', 'created_at', 'embedding']


class DocumentSerializer(serializers.ModelSerializer):
    """Lightweight listing serializer — does NOT embed chunk content to avoid huge payloads."""
    chunk_count = serializers.IntegerField(source='chunks.count', read_only=True)

    class Meta:
        model = Document
        fields = [
            'id', 'title', 'source', 'status', 'chunk_count',
            'file_url', 'original_filename', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'status', 'chunk_count', 'file_url',
            'original_filename', 'created_at', 'updated_at',
        ]


class DocumentUploadSerializer(serializers.ModelSerializer):
    """
    Handles document upload:
      1. Validates file type (.pdf / .txt) and size (≤ 10 MB).
      2. Uploads file bytes to Supabase Storage.
      3. Saves Document row with the Supabase URL.
    """
    file = serializers.FileField(write_only=True)

    class Meta:
        model = Document
        fields = ['id', 'title', 'file', 'source']

    # ── Validation ──────────────────────────────────────────────────────────────

    def validate_file(self, value):
        allowed_extensions = ['.pdf', '.txt']
        file_ext = '.' + value.name.rsplit('.', 1)[-1].lower()
        if file_ext not in allowed_extensions:
            raise serializers.ValidationError(
                f"Unsupported file format. Allowed: {', '.join(allowed_extensions)}"
            )
        max_size = 10 * 1024 * 1024  # 10 MB
        if value.size > max_size:
            raise serializers.ValidationError(
                f"File too large: {value.size // (1024 * 1024)} MB. Maximum allowed size is 10 MB."
            )
        return value

    # ── Create ──────────────────────────────────────────────────────────────────

    def create(self, validated_data):
        file_obj = validated_data.pop('file')

        # Read file into memory (avoids any disk write)
        file_bytes = file_obj.read()
        original_filename = file_obj.name
        file_ext = '.' + original_filename.rsplit('.', 1)[-1].lower()

        # Generate a unique storage path to prevent collisions
        storage_path = f"{uuid.uuid4().hex}{file_ext}"

        # ── Upload to Supabase Storage ──────────────────────────────────────────
        file_url = _upload_to_supabase(file_bytes, storage_path, file_ext)

        # ── Create Document row ─────────────────────────────────────────────────
        document = Document.objects.create(
            **validated_data,
            file_url=file_url,
            original_filename=original_filename,
        )
        return document


# ── Supabase helper ─────────────────────────────────────────────────────────────

def _upload_to_supabase(file_bytes: bytes, storage_path: str, file_ext: str) -> str:
    """
    Upload file bytes to Supabase Storage bucket.
    Returns the public URL of the uploaded file.
    Raises serializers.ValidationError on failure.
    """
    from supabase import create_client

    supabase_url = getattr(settings, 'SUPABASE_URL', '')
    supabase_key = getattr(settings, 'SUPABASE_KEY', '')
    bucket_name = getattr(settings, 'SUPABASE_BUCKET', 'ai-customer-support-pdfs')

    if not supabase_url or not supabase_key:
        raise serializers.ValidationError(
            "Supabase is not configured. Set SUPABASE_URL and SUPABASE_KEY."
        )

    content_type_map = {
        '.pdf': 'application/pdf',
        '.txt': 'text/plain',
    }
    content_type = content_type_map.get(file_ext, 'application/octet-stream')

    try:
        client = create_client(supabase_url, supabase_key)
        client.storage.from_(bucket_name).upload(
            path=storage_path,
            file=file_bytes,
            file_options={
                'content-type': content_type,
                'upsert': 'false',
            },
        )
        # Build the public URL
        public_url = f"{supabase_url}/storage/v1/object/public/{bucket_name}/{storage_path}"
        logger.info("Uploaded %s to Supabase bucket '%s' → %s", storage_path, bucket_name, public_url)
        return public_url

    except Exception as exc:
        logger.exception("Supabase upload failed for path '%s': %s", storage_path, exc)
        raise serializers.ValidationError(
            f"File upload to storage failed: {exc}"
        )


# ── Remaining serializers (unchanged) ──────────────────────────────────────────

class ConversationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversation
        fields = ['id', 'user', 'title', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['id', 'conversation', 'role', 'content', 'tokens_used', 'created_at']
        read_only_fields = ['id', 'created_at', 'tokens_used']


class EscalationTicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = EscalationTicket
        fields = ['id', 'conversation', 'issue', 'priority', 'status', 'assigned_to',
                  'agent_reply', 'created_at', 'updated_at', 'resolved_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class TicketListSerializer(serializers.ModelSerializer):
    """Read-only serializer for the priority-ordered ticket queue."""
    conversation_title = serializers.SerializerMethodField()

    class Meta:
        model = EscalationTicket
        fields = ['id', 'conversation', 'conversation_title', 'issue', 'priority',
                  'status', 'assigned_to', 'agent_reply', 'created_at', 'updated_at',
                  'resolved_at']
        read_only_fields = fields

    def get_conversation_title(self, obj):
        return obj.conversation.title if obj.conversation else None


class TicketResolveSerializer(serializers.ModelSerializer):
    """Write serializer for resolving a ticket with an agent reply."""

    class Meta:
        model = EscalationTicket
        fields = ['id', 'agent_reply', 'status', 'resolved_at']
        read_only_fields = ['id', 'resolved_at']

    def validate_agent_reply(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("agent_reply cannot be empty when resolving a ticket.")
        return value.strip()

    def update(self, instance, validated_data):
        from django.utils import timezone
        instance.agent_reply = validated_data.get('agent_reply', instance.agent_reply)
        instance.status = 'resolved'
        instance.resolved_at = timezone.now()
        instance.save()
        return instance


class RAGAskSerializer(serializers.Serializer):
    question = serializers.CharField(max_length=4000)
    top_k = serializers.IntegerField(required=False, min_value=1, max_value=20, default=5)
    conversation_id = serializers.IntegerField(required=False)

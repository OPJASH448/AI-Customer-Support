from rest_framework import serializers
from .models import Document, DocumentChunk, Conversation, Message, EscalationTicket


class DocumentChunkSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentChunk
        fields = ['id', 'document', 'content', 'chunk_index', 'tokens', 'created_at']
        read_only_fields = ['id', 'created_at', 'embedding']


class DocumentSerializer(serializers.ModelSerializer):
    chunks = DocumentChunkSerializer(many=True, read_only=True)
    chunk_count = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = ['id', 'title', 'source', 'status', 'chunk_count', 'chunks', 'created_at', 'updated_at']
        read_only_fields = ['id', 'status', 'created_at', 'updated_at']

    def get_chunk_count(self, obj):
        return obj.chunks.count()


class DocumentUploadSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True)

    class Meta:
        model = Document
        fields = ['id', 'title', 'file', 'source']

    def validate_file(self, value):
        allowed_extensions = ['.pdf', '.txt']
        file_ext = ''.join(['.', value.name.split('.')[-1]]).lower()
        if file_ext not in allowed_extensions:
            raise serializers.ValidationError(
                f"Unsupported file format. Allowed: {', '.join(allowed_extensions)}"
            )
        if value.size > 50 * 1024 * 1024:  # 50MB limit
            raise serializers.ValidationError("File size must not exceed 50MB.")
        return value

    def create(self, validated_data):
        file_obj = validated_data.pop('file')
        document = Document.objects.create(
            **validated_data
        )
        # Save file to media folder
        document.file = file_obj
        document.save()
        return document


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

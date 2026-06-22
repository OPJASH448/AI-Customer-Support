from django.contrib import admin
from .models import Document, DocumentChunk, Conversation, Message, EscalationTicket


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'status', 'source', 'original_filename', 'uploaded_by', 'is_active', 'created_at')
    list_filter = ('status', 'is_active', 'created_at')
    search_fields = ('title', 'content', 'source', 'original_filename')
    readonly_fields = ('file_url', 'original_filename', 'created_at', 'updated_at')
    list_per_page = 25
    date_hierarchy = 'created_at'


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    list_display = ('id', 'document', 'chunk_index', 'tokens', 'has_embedding', 'created_at')
    list_filter = ('document', 'created_at')
    search_fields = ('document__title', 'content')
    readonly_fields = ('created_at',)
    list_per_page = 25

    @admin.display(boolean=True, description='Embedded')
    def has_embedding(self, obj):
        return obj.embedding is not None


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'title', 'message_count', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active', 'created_at', 'user')
    search_fields = ('title', 'user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 25
    date_hierarchy = 'created_at'

    @admin.display(description='Messages')
    def message_count(self, obj):
        return obj.messages.count()


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'role', 'content_preview', 'tokens_used', 'chunk_count', 'created_at')
    list_filter = ('role', 'created_at')
    search_fields = ('content', 'conversation__title', 'conversation__user__username')
    readonly_fields = ('created_at',)
    list_per_page = 25

    @admin.display(description='Preview')
    def content_preview(self, obj):
        return obj.content[:80] + '...' if len(obj.content) > 80 else obj.content

    @admin.display(description='Context Chunks')
    def chunk_count(self, obj):
        return obj.context_chunks.count()


@admin.register(EscalationTicket)
class EscalationTicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'priority', 'status', 'issue_preview', 'assigned_to',
                    'has_reply', 'created_at', 'resolved_at')
    list_filter = ('status', 'priority', 'created_at', 'assigned_to')
    search_fields = ('issue', 'agent_reply', 'conversation__title', 'conversation__user__username')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 25
    date_hierarchy = 'created_at'
    list_editable = ('status', 'priority', 'assigned_to')

    @admin.display(description='Issue')
    def issue_preview(self, obj):
        return obj.issue[:100] + '...' if len(obj.issue) > 100 else obj.issue

    @admin.display(boolean=True, description='Replied')
    def has_reply(self, obj):
        return bool(obj.agent_reply)

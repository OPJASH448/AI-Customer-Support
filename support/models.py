from django.db import models
from django.contrib.auth.models import User
from pgvector.django import VectorField

class Document(models.Model):
    """
    Base document model for RAG system.
    Stores uploaded documents with metadata.
    """
    STATUS_CHOICES = [
        ('processing', 'Processing'),
        ('ready', 'Ready'),
        ('failed', 'Failed'),
    ]
    
    title = models.CharField(max_length=255)
    content = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to='documents/', blank=True, null=True)
    source = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='processing')
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']


class DocumentChunk(models.Model):
    """
    Vector embeddings for document chunks.
    Each document is split into chunks and embedded with pgvector.
    """
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='chunks')
    content = models.TextField()
    chunk_index = models.IntegerField()
    embedding = VectorField(dimensions=768)  # Google Gemini embedding dimension
    tokens = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.document.title} - Chunk {self.chunk_index}"

    class Meta:
        ordering = ['document', 'chunk_index']
        indexes = [
            models.Index(fields=['document']),
        ]


class Conversation(models.Model):
    """
    Tracks conversations between users and the AI support agent.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations')
    title = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title or f"Conversation #{self.id}"

    class Meta:
        ordering = ['-updated_at']


class Message(models.Model):
    """
    Individual messages in a conversation.
    """
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
    ]

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    tokens_used = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # RAG context
    context_chunks = models.ManyToManyField(DocumentChunk, blank=True, related_name='used_in_messages')

    def __str__(self):
        return f"{self.conversation.id} - {self.role}"

    class Meta:
        ordering = ['created_at']


class EscalationTicket(models.Model):
    """
    Tracks issues that need human escalation.
    """
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    conversation = models.ForeignKey(Conversation, on_delete=models.SET_NULL, null=True, blank=True)
    issue = models.TextField()
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tickets')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Ticket #{self.id} - {self.priority.upper()}"

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'priority']),
        ]

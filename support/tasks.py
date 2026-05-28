from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
import openai
import json

openai.api_key = settings.OPENAI_API_KEY


@shared_task
def embed_document_chunks(document_id):
    """
    Generate embeddings for all chunks of a document.
    Called asynchronously after document upload.
    """
    from .models import Document, DocumentChunk
    
    try:
        document = Document.objects.get(id=document_id)
        chunks = document.chunks.all()
        
        for chunk in chunks:
            # Generate embedding using OpenAI
            response = openai.Embedding.create(
                input=chunk.content,
                model="text-embedding-ada-002"
            )
            
            embedding_vector = response['data'][0]['embedding']
            chunk.embedding = embedding_vector
            chunk.save()
        
        return f"Successfully embedded {chunks.count()} chunks for document {document.title}"
    
    except Exception as e:
        return f"Error embedding document {document_id}: {str(e)}"


@shared_task
def escalate_conversation(conversation_id, reason):
    """
    Create escalation ticket and notify support team.
    """
    from .models import Conversation, EscalationTicket
    
    try:
        conversation = Conversation.objects.get(id=conversation_id)
        ticket = EscalationTicket.objects.create(
            conversation=conversation,
            issue=reason,
            priority='high'
        )
        
        # Send notification email
        send_mail(
            subject=f"New Support Escalation: Ticket #{ticket.id}",
            message=f"Conversation {conversation_id} requires human review.\nReason: {reason}",
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[admin[1] for admin in settings.ADMINS],
        )
        
        return f"Escalation ticket #{ticket.id} created"
    
    except Exception as e:
        return f"Error escalating conversation {conversation_id}: {str(e)}"


@shared_task
def cleanup_old_conversations(days=30):
    """
    Archive old inactive conversations.
    Run periodically via Celery Beat.
    """
    from django.utils import timezone
    from datetime import timedelta
    from .models import Conversation
    
    cutoff_date = timezone.now() - timedelta(days=days)
    old_convos = Conversation.objects.filter(
        updated_at__lt=cutoff_date,
        is_active=True
    )
    
    count = old_convos.update(is_active=False)
    return f"Archived {count} old conversations"

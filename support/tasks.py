from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
import json
import os
import google.generativeai as genai

# Configure Gemini
genai.configure(api_key=os.environ.get('GEMINI_API_KEY') or settings.GEMINI_API_KEY)


@shared_task
def test_celery_task():
    """
    Dummy task to test Celery + Redis connection.
    Should return immediately.
    """
    return {
        'status': 'success',
        'message': 'Celery + Redis is working correctly!',
        'timestamp': str(__import__('django.utils.timezone', fromlist=['now']).now())
    }


@shared_task
def process_document(document_id):
    """
    Main document processing task:
    1. Extract text from PDF/TXT
    2. Split into 500-token chunks with 50-token overlap
    3. Call OpenAI text-embedding-3-small for each chunk
    4. Save DocumentChunk with embeddings to pgvector
    5. Update Document status to 'ready' or 'failed'
    """
    from .models import Document, DocumentChunk
    from PyPDF2 import PdfReader
    import tiktoken
    
    try:
        document = Document.objects.get(id=document_id)
        document.status = 'processing'
        document.save()
        
        # Extract text from file
        if not document.file:
            raise ValueError("Document has no associated file")
        
        file_path = document.file.path
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # Extract text based on file type
        if file_ext == '.pdf':
            text = extract_text_from_pdf(file_path)
        elif file_ext == '.txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
        else:
            raise ValueError(f"Unsupported file type: {file_ext}")
        
        if not text or len(text.strip()) == 0:
            raise ValueError("Extracted text is empty")
        
        # Split into chunks (500 tokens, 50-token overlap)
        chunks = split_into_chunks(text, chunk_size=500, overlap=50)
        
        # Embed chunks in batches of 20
        chunk_objects = []
        for i, chunk_text in enumerate(chunks):
            embedding = get_embedding(chunk_text)
            
            chunk_obj = DocumentChunk(
                document=document,
                content=chunk_text,
                chunk_index=i,
                embedding=embedding,
                tokens=count_tokens(chunk_text)
            )
            chunk_objects.append(chunk_obj)
        
        # Bulk create chunks
        DocumentChunk.objects.bulk_create(chunk_objects)
        
        # Update document status to ready
        document.status = 'ready'
        document.save()
        
        return {
            'status': 'success',
            'document_id': document_id,
            'chunks_created': len(chunk_objects),
            'message': f'Successfully processed {len(chunk_objects)} chunks'
        }
    
    except Exception as e:
        # Update document status to failed on error
        try:
            document = Document.objects.get(id=document_id)
            document.status = 'failed'
            document.save()
        except:
            pass
        
        return {
            'status': 'failed',
            'document_id': document_id,
            'error': str(e)
        }


def extract_text_from_pdf(file_path):
    """Extract text from PDF using PyPDF2"""
    text = []
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PdfReader(file)
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text.append(page_text)
        return '\n'.join(text)
    except Exception as e:
        raise ValueError(f"Error extracting text from PDF: {str(e)}")


def split_into_chunks(text, chunk_size=500, overlap=50):
    """
    Split text into chunks with specified token size and overlap.
    Uses a sliding window approach.
    """
    import tiktoken
    
    encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
    tokens = encoding.encode(text)
    
    chunks = []
    start = 0
    
    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_text = encoding.decode(chunk_tokens)
        
        if chunk_text.strip():
            chunks.append(chunk_text)
        
        # Move start position by (chunk_size - overlap)
        start = end - overlap if end < len(tokens) else len(tokens)
    
    return chunks


def count_tokens(text):
    """Count tokens in text using tiktoken"""
    import tiktoken
    encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
    return len(encoding.encode(text))


def get_embedding(text):
    """Call Google Gemini API for embeddings"""
    try:
        result = genai.embed_content(
            model="models/gemini-embedding-001",
            content=text,
            output_dimensionality=768
        )
        return result['embedding']
    except Exception as e:
        raise ValueError(f"Error getting embedding from Gemini: {str(e)}")


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
        
        # Send notification email if configured
        try:
            send_mail(
                subject=f"New Support Escalation: Ticket #{ticket.id}",
                message=f"Conversation {conversation_id} requires human review.\nReason: {reason}",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[admin[1] for admin in settings.ADMINS],
            )
        except:
            pass  # Email sending is optional
        
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
    
    try:
        cutoff_date = timezone.now() - timedelta(days=days)
        old_convos = Conversation.objects.filter(
            updated_at__lt=cutoff_date
        )
        
        count = old_convos.count()
        old_convos.delete()
        
        return f"Cleaned up {count} old conversations"
    except Exception as e:
        return f"Error cleaning conversations: {str(e)}"

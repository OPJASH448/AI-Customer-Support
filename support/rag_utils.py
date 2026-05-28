"""
RAG (Retrieval Augmented Generation) utilities for vector search and LLM integration.
"""
import openai
from django.conf import settings
from .models import DocumentChunk, Message

openai.api_key = settings.OPENAI_API_KEY


def embed_text(text: str) -> list:
    """
    Generate embedding for text using OpenAI API.
    Returns vector of dimension 1536.
    """
    try:
        response = openai.Embedding.create(
            input=text,
            model="text-embedding-ada-002"
        )
        return response['data'][0]['embedding']
    except Exception as e:
        raise Exception(f"Failed to generate embedding: {str(e)}")


def retrieve_context(query: str, top_k: int = 5) -> list:
    """
    Retrieve most relevant document chunks using vector similarity.
    Uses pgvector distance operator <-> for cosine similarity.
    """
    try:
        query_embedding = embed_text(query)
        
        # Query using pgvector similarity search
        chunks = DocumentChunk.objects.raw(
            f"""
            SELECT * FROM support_documentchunk
            ORDER BY embedding <-> %s
            LIMIT %s
            """,
            [query_embedding, top_k]
        )
        
        return list(chunks)
    
    except Exception as e:
        print(f"Error retrieving context: {str(e)}")
        return []


def generate_response(query: str, conversation_id: int) -> dict:
    """
    Generate AI response using retrieved context (RAG).
    
    Returns:
        {
            'response': str,
            'context_chunks': [DocumentChunk],
            'tokens_used': int
        }
    """
    try:
        # Retrieve relevant context
        context_chunks = retrieve_context(query, top_k=5)
        context_text = "\n".join([chunk.content for chunk in context_chunks])
        
        # Build prompt
        system_prompt = """You are a helpful AI customer support agent. 
Use the provided context to answer customer questions accurately and helpfully.
If you're unsure, ask clarifying questions or offer to escalate to a human agent."""
        
        user_prompt = f"""Context Information:
{context_text}

Customer Question:
{query}

Provide a helpful, accurate response based on the context."""
        
        # Get response from OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        assistant_message = response['choices'][0]['message']['content']
        tokens_used = response['usage']['total_tokens']
        
        # Save to database
        from .models import Conversation
        conversation = Conversation.objects.get(id=conversation_id)
        
        message = Message.objects.create(
            conversation=conversation,
            role='assistant',
            content=assistant_message,
            tokens_used=tokens_used
        )
        message.context_chunks.set(context_chunks)
        
        return {
            'response': assistant_message,
            'context_chunks': context_chunks,
            'tokens_used': tokens_used
        }
    
    except Exception as e:
        raise Exception(f"Failed to generate response: {str(e)}")


def split_document_into_chunks(content: str, chunk_size: int = 500, overlap: int = 100) -> list:
    """
    Split document content into overlapping chunks.
    """
    chunks = []
    step = chunk_size - overlap
    
    for i in range(0, len(content), step):
        chunk_text = content[i:i + chunk_size]
        if len(chunk_text) > 100:  # Only include substantial chunks
            chunks.append(chunk_text)
    
    return chunks

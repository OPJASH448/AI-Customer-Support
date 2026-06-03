"""
RAG (Retrieval Augmented Generation) utilities for vector search and LLM integration.
Uses Google Gemini for embeddings and generation.
"""
import os
import google.generativeai as genai
from django.conf import settings
from .models import DocumentChunk, Message

# Configure Gemini
genai.configure(api_key=os.environ.get('GEMINI_API_KEY') or settings.GEMINI_API_KEY)


def embed_text(text: str) -> list:
    """
    Generate embedding for text using Google Gemini API.
    Returns vector of dimension 768.
    """
    try:
        result = genai.embed_content(
            model="models/gemini-embedding-001",
            content=text,
            output_dimensionality=768
        )
        return result['embedding']
    except Exception as e:
        raise Exception(f"Failed to generate embedding: {str(e)}")


def split_query_into_chunks(query: str, chunk_size: int = 300, overlap: int = 100) -> list:
    """
    Split user query into chunks if it is too long.
    This helps in high-accuracy RAG by preventing embedding dilution of long queries.
    """
    query = query.strip()
    if len(query) <= 400:
        return [query]

    import re
    sentences = re.split(r'(?<=[.!?])\s+', query)
    
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) <= chunk_size:
            current_chunk = (current_chunk + " " + sentence).strip()
        else:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = sentence
            
    if current_chunk:
        chunks.append(current_chunk)
        
    if not chunks:
        step = chunk_size - overlap
        for i in range(0, len(query), step):
            c = query[i:i + chunk_size].strip()
            if c:
                chunks.append(c)
                
    return chunks


def embed_query_chunks(chunks: list) -> list:
    """Generate embeddings for list of query chunks in batch via Gemini."""
    if not chunks:
        return []
    if len(chunks) == 1:
        return [embed_text(chunks[0])]
    
    try:
        result = genai.embed_content(
            model="models/gemini-embedding-001",
            content=chunks,
            output_dimensionality=768,
        )
        return result['embedding']
    except Exception as e:
        embeddings = []
        for chunk in chunks:
            embeddings.append(embed_text(chunk))
        return embeddings


def retrieve_context(query: str, top_k: int = 5) -> list:
    """
    Retrieve most relevant document chunks using vector similarity.
    Supports query chunking and Reciprocal Rank Fusion (RRF) for high accuracy.
    Uses pgvector distance operator <=> for cosine similarity.
    """
    try:
        query_chunks = split_query_into_chunks(query)
        query_embeddings = embed_query_chunks(query_chunks)
        
        if not query_embeddings:
            return []
            
        from collections import defaultdict
        chunk_scores = defaultdict(float)
        chunk_map = {}
        
        for q_emb in query_embeddings:
            # Query using pgvector similarity search
            chunks = DocumentChunk.objects.raw(
                """
                SELECT * FROM support_documentchunk
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                [q_emb, top_k]
            )
            for rank, chunk in enumerate(chunks, 1):
                chunk_scores[chunk.id] += 1.0 / rank
                chunk_map[chunk.id] = chunk
                
        sorted_ids = sorted(chunk_scores.keys(), key=lambda cid: chunk_scores[cid], reverse=True)[:top_k]
        return [chunk_map[cid] for cid in sorted_ids]

    except Exception as e:
        print(f"Error retrieving context: {str(e)}")
        return []


def generate_response(query: str, conversation_id: int) -> dict:
    """
    Generate AI response using retrieved context (RAG) via Gemini.

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

        # Get response from Gemini
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(
            f"{system_prompt}\n\n{user_prompt}",
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=500,
            )
        )

        assistant_message = response.text
        # Gemini doesn't return exact token counts in the same way,
        # estimate from usage_metadata if available
        tokens_used = 0
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            tokens_used = (
                getattr(response.usage_metadata, 'prompt_token_count', 0) +
                getattr(response.usage_metadata, 'candidates_token_count', 0)
            )

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

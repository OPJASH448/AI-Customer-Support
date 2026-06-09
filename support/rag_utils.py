"""
RAG Utilities — Hybrid RAG support functions.
Uses google-genai SDK (replaces deprecated google-generativeai).

Primary retrieval is handled by support.rag.hybrid_retrieve().
This module provides:
  - embed_text()                  — Gemini embedding wrapper (google-genai SDK)
  - retrieve_context()            — Calls hybrid_retrieve() for full Hybrid RAG
  - generate_response()           — RAG response generation with DB persistence
  - split_document_into_chunks()  — Used during document ingestion
"""
import os
from google import genai
from google.genai import types as genai_types
from django.conf import settings
from .models import DocumentChunk, Message

# ── Gemini client (new google-genai SDK) ──────────────────────────────────────
_client = genai.Client(
    api_key=os.environ.get("GEMINI_API_KEY") or settings.GEMINI_API_KEY
)

EMBED_MODEL = "gemini-embedding-001"
GEN_MODEL = "gemini-2.0-flash"


def embed_text(text: str) -> list:
    """
    Generate 768-dim embedding for text using Google Gemini API (google-genai SDK).
    """
    try:
        response = _client.models.embed_content(
            model=EMBED_MODEL,
            contents=text,
            config=genai_types.EmbedContentConfig(output_dimensionality=768),
        )
        return list(response.embeddings[0].values)
    except Exception as e:
        raise Exception(f"Failed to generate embedding: {str(e)}")


def retrieve_context(query: str, top_k: int = 5, user=None) -> list:
    """
    Retrieve the most relevant document chunks using Hybrid RAG.

    Internally calls hybrid_retrieve() which runs:
      1) Dense  — pgvector HNSW cosine similarity (Gemini embeddings)
      2) Sparse — BM25 keyword search (rank_bm25, in-memory)
      3) Fusion — Reciprocal Rank Fusion (RRF, k=60)
    """
    try:
        from .rag import hybrid_retrieve
        return hybrid_retrieve(question=query, user=user, top_k=top_k)
    except Exception as e:
        print(f"[retrieve_context] Hybrid RAG error: {e}")
        return []


def generate_response(query: str, conversation_id: int, user=None) -> dict:
    """
    Generate AI response using Hybrid RAG context via Gemini (google-genai SDK).

    Returns dict with keys: 'response', 'context_chunks', 'tokens_used'
    """
    try:
        # ── Hybrid retrieval ──────────────────────────────────────────────────
        context_chunks = retrieve_context(query, top_k=5, user=user)
        context_text = "\n".join([chunk.content for chunk in context_chunks])

        # ── Build prompt ──────────────────────────────────────────────────────
        full_prompt = (
            "You are a helpful AI customer support agent.\n"
            "Use the provided context to answer customer questions accurately.\n"
            "Cite document names in [brackets] after each fact.\n"
            "If context is insufficient, ask clarifying questions or offer escalation.\n\n"
            f"Context Information:\n{context_text}\n\n"
            f"Customer Question:\n{query}\n\n"
            "Provide a helpful, accurate response based on the context."
        )

        # ── Gemini generation ─────────────────────────────────────────────────
        response = _client.models.generate_content(
            model=GEN_MODEL,
            contents=full_prompt,
            config=genai_types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=500,
            ),
        )

        assistant_message = response.text
        tokens_used = 0
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            tokens_used = (
                getattr(response.usage_metadata, "prompt_token_count", 0) +
                getattr(response.usage_metadata, "candidates_token_count", 0)
            )

        # ── Persist to DB ─────────────────────────────────────────────────────
        from .models import Conversation
        conversation = Conversation.objects.get(id=conversation_id)

        message = Message.objects.create(
            conversation=conversation,
            role="assistant",
            content=assistant_message,
            tokens_used=tokens_used,
        )
        message.context_chunks.set(context_chunks)

        return {
            "response": assistant_message,
            "context_chunks": context_chunks,
            "tokens_used": tokens_used,
        }

    except Exception as e:
        raise Exception(f"Failed to generate response: {str(e)}")


def split_document_into_chunks(content: str, chunk_size: int = 500, overlap: int = 100) -> list:
    """
    Split document content into overlapping character-level chunks.
    Used as a simple fallback; tasks.py handles token-level splitting with tiktoken.
    """
    chunks = []
    step = chunk_size - overlap
    for i in range(0, len(content), step):
        chunk_text = content[i:i + chunk_size]
        if len(chunk_text) > 100:
            chunks.append(chunk_text)
    return chunks

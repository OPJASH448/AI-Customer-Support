"""
RAG Chat Endpoint — POST /api/chat/

Full pipeline: embed query → pgvector cosine search → build context → Gemini 2.0 Flash → cited answer → auto-escalation
"""
import os
import json
from datetime import datetime

import google.generativeai as genai
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from .models import Document, DocumentChunk, Conversation, Message, EscalationTicket
from .token_logger import log_token_usage

# Configure Gemini
genai.configure(api_key=os.environ.get('GEMINI_API_KEY') or settings.GEMINI_API_KEY)

# ─── Constants ────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an AI customer support agent. Answer questions ONLY based on the provided context documents.

Rules:
1. ONLY use information from the provided context to answer the question.
2. Cite your sources by putting the document name in [brackets] after each claim.
   Example: "The motor uses PWM control [Motor Guide]."
3. If the context does NOT contain enough information to answer, respond EXACTLY with:
   "I don't know based on the available documents."
4. Be helpful, concise, and accurate.
5. Never fabricate information that is not present in the context.
6. If multiple documents support a fact, cite all of them."""

INABILITY_PHRASES = [
    "i don't know",
    "i do not know",
    "don't have enough information",
    "insufficient information",
    "not enough information",
    "cannot answer",
    "can't answer",
    "unable to answer",
    "no relevant information",
    "not found in the available",
    "not mentioned in",
    "beyond the scope",
    "outside the provided context",
    "the context does not",
    "the documents do not",
    "i'm not sure based on",
]

# Keyword → priority score mapping (higher = more urgent)
URGENCY_KEYWORDS = {
    5: ['urgent', 'critical', 'emergency', 'severe', 'immediately', 'asap', 'crash', 'down', 'outage', 'security breach'],
    4: ['important', 'broken', 'failing', 'not working', 'blocked', 'production', 'deadline'],
    3: ['help', 'issue', 'problem', 'error', 'bug', 'trouble', 'wrong', 'fix'],
    2: ['question', 'wondering', 'curious', 'how to', 'what is', 'explain'],
    1: ['general', 'feedback', 'suggestion', 'info', 'thanks'],
}

PRIORITY_MAP = {
    5: 'critical',
    4: 'high',
    3: 'medium',
    2: 'low',
    1: 'low',
}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def split_query_into_chunks(query: str, chunk_size: int = 300, overlap: int = 100) -> list:
    """
    Split user query into chunks if it is too long.
    This helps in high-accuracy RAG by preventing embedding dilution of long queries.
    """
    query = query.strip()
    if len(query) <= 400:
        return [query]

    # Split by sentence or fallback to word-based chunks
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
        
    # If chunks are too small or we got 0, fallback to character window
    if not chunks:
        step = chunk_size - overlap
        for i in range(0, len(query), step):
            c = query[i:i + chunk_size].strip()
            if c:
                chunks.append(c)
                
    return chunks


def embed_query_chunks(chunks: list) -> list:
    """Generate 768-dim embeddings for list of query chunks in batch via Gemini."""
    if not chunks:
        return []
    # If single chunk, call normally
    if len(chunks) == 1:
        result = genai.embed_content(
            model="models/gemini-embedding-001",
            content=chunks[0],
            output_dimensionality=768,
        )
        return [result['embedding']]
    
    # Batch call for multiple chunks
    try:
        result = genai.embed_content(
            model="models/gemini-embedding-001",
            content=chunks,
            output_dimensionality=768,
        )
        return result['embedding']
    except Exception as e:
        # Fallback to single embedding generation if batch fails
        embeddings = []
        for chunk in chunks:
            res = genai.embed_content(
                model="models/gemini-embedding-001",
                content=chunk,
                output_dimensionality=768,
            )
            embeddings.append(res['embedding'])
        return embeddings


def fused_vector_search(query_embeddings: list, top_k: int = 5) -> list:
    """
    pgvector cosine distance search for multiple query embeddings.
    Combines results using Reciprocal Rank Fusion (RRF) to select top_k unique chunks.
    """
    if not query_embeddings:
        return []
    
    from collections import defaultdict
    chunk_scores = defaultdict(float)
    chunk_map = {}
    
    for q_emb in query_embeddings:
        chunks = DocumentChunk.objects.raw(
            """
            SELECT dc.*, d.title AS doc_title
            FROM support_documentchunk dc
            JOIN support_document d ON dc.document_id = d.id
            WHERE d.status = 'ready' AND d.is_active = true
            ORDER BY dc.embedding <=> %s::vector
            LIMIT %s
            """,
            [q_emb, top_k],
        )
        for rank, chunk in enumerate(chunks, 1):
            # Reciprocal rank fusion: 1 / rank
            chunk_scores[chunk.id] += 1.0 / rank
            chunk_map[chunk.id] = chunk
            
    # Sort chunks by highest score first
    sorted_ids = sorted(chunk_scores.keys(), key=lambda cid: chunk_scores[cid], reverse=True)[:top_k]
    return [chunk_map[cid] for cid in sorted_ids]


def embed_query(text: str) -> list:
    """Generate 768-dim embedding for user query via Gemini."""
    result = genai.embed_content(
        model="models/gemini-embedding-001",
        content=text,
        output_dimensionality=768,
    )
    return result['embedding']


def vector_search(query_embedding: list, top_k: int = 5) -> list:
    """
    pgvector cosine distance search.
    Uses the <=> operator (cosine distance) — ORDER BY ascending = most similar first.
    """
    chunks = DocumentChunk.objects.raw(
        """
        SELECT dc.*, d.title AS doc_title
        FROM support_documentchunk dc
        JOIN support_document d ON dc.document_id = d.id
        WHERE d.status = 'ready' AND d.is_active = true
        ORDER BY dc.embedding <=> %s::vector
        LIMIT %s
        """,
        [query_embedding, top_k],
    )
    return list(chunks)


def build_context(chunks: list) -> tuple:
    """
    Join top chunks with source document name prefixed.
    Returns (context_string, deduplicated_sources_list).
    """
    context_parts = []
    sources = []
    for chunk in chunks:
        doc_title = chunk.document.title
        context_parts.append(f"[{doc_title}]: {chunk.content}")
        if doc_title not in sources:
            sources.append(doc_title)
    return "\n\n".join(context_parts), sources


def score_priority(user_message: str) -> int:
    """Score urgency 1–5 based on keywords in the user message."""
    lower = user_message.lower()
    for score in [5, 4, 3, 2, 1]:
        if any(kw in lower for kw in URGENCY_KEYWORDS[score]):
            return score
    return 1  # default: lowest


def detect_escalation(assistant_text: str) -> bool:
    """Return True if the assistant's answer contains inability / low-confidence phrases."""
    lower = assistant_text.lower()
    return any(phrase in lower for phrase in INABILITY_PHRASES)


# ─── Main View ────────────────────────────────────────────────────────────────

class ChatView(APIView):
    """
    POST /api/chat/

    Body (JSON):
        {
            "user_message": "How does the motor work?",
            "conversation_id": 1          // optional — omit to auto-create
        }

    Response:
        {
            "answer": "The motor uses PWM... [Motor Guide]",
            "sources": ["Motor Guide"],
            "escalated": false,
            "ticket_id": null,
            "conversation_id": 1,
            "tokens_used": { "prompt": 350, "completion": 120, "total": 470 }
        }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user_message = request.data.get('user_message', '').strip()
        conversation_id = request.data.get('conversation_id')

        # ── Validate ──────────────────────────────────────────────────────
        if not user_message:
            return Response(
                {'error': 'user_message is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Get or create conversation ────────────────────────────────────
        try:
            if conversation_id:
                conversation = Conversation.objects.get(
                    id=conversation_id, user=request.user,
                )
            else:
                conversation = Conversation.objects.create(
                    user=request.user,
                    title=user_message[:100],
                )
        except Conversation.DoesNotExist:
            return Response(
                {'error': f'Conversation {conversation_id} not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # ── Save user message ─────────────────────────────────────────────
        user_msg = Message.objects.create(
            conversation=conversation,
            role='user',
            content=user_message,
        )

        # ── Step 1: Chunk query if needed & embed ─────────────────────────
        try:
            query_chunks = split_query_into_chunks(user_message)
            query_embeddings = embed_query_chunks(query_chunks)
        except Exception as e:
            return Response(
                {'error': f'Embedding failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # ── Step 2: Fused pgvector cosine search (top 5) ──────────────────
        chunks = fused_vector_search(query_embeddings, top_k=5)

        if not chunks:
            # No documents in the knowledge base yet
            context_text = "(No documents available in the knowledge base.)"
            sources = []
        else:
            context_text, sources = build_context(chunks)

        # ── Step 3: Build prompt & call Gemini 2.0 Flash ──────────────────
        user_prompt = f"""Context Documents:
{context_text}

Customer Question:
{user_message}

Provide a helpful, accurate answer. Cite document names in [brackets]."""

        try:
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content(
                f"{SYSTEM_PROMPT}\n\n{user_prompt}",
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=1000,
                ),
            )
            assistant_text = response.text
        except Exception as e:
            return Response(
                {'error': f'Gemini generation failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # ── Step 4: Extract token usage ───────────────────────────────────
        prompt_tokens = 0
        completion_tokens = 0
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            prompt_tokens = getattr(response.usage_metadata, 'prompt_token_count', 0) or 0
            completion_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0) or 0
        total_tokens = prompt_tokens + completion_tokens

        # ── Step 5: Log tokens to file ────────────────────────────────────
        log_token_usage(
            user_id=request.user.id,
            username=request.user.username,
            conversation_id=conversation.id,
            user_message=user_message,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )

        # ── Step 6: Save assistant message ────────────────────────────────
        assistant_msg = Message.objects.create(
            conversation=conversation,
            role='assistant',
            content=assistant_text,
            tokens_used=total_tokens,
        )
        if chunks:
            assistant_msg.context_chunks.set(chunks)

        # ── Step 7: Escalation detection ──────────────────────────────────
        escalated = False
        ticket_id = None

        if detect_escalation(assistant_text):
            priority_score = score_priority(user_message)
            priority_label = PRIORITY_MAP.get(priority_score, 'medium')

            ticket = EscalationTicket.objects.create(
                conversation=conversation,
                issue=f"AI unable to answer (priority {priority_score}/5): {user_message}",
                priority=priority_label,
                status='open',
            )
            escalated = True
            ticket_id = ticket.id

        # ── Return response ───────────────────────────────────────────────
        return Response({
            'answer': assistant_text,
            'sources': sources,
            'escalated': escalated,
            'ticket_id': ticket_id,
            'conversation_id': conversation.id,
            'tokens_used': {
                'prompt': prompt_tokens,
                'completion': completion_tokens,
                'total': total_tokens,
            },
        })

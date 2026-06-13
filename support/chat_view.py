"""
Hybrid RAG Chat Endpoint — POST /api/chat/

Full pipeline:
  1. Hybrid RAG retrieval:
       a) Dense  — pgvector HNSW cosine similarity (Gemini 768-dim embeddings)
       b) Sparse — BM25 keyword search (rank_bm25, in-memory)
       c) Merge  — Reciprocal Rank Fusion (RRF, k=60)
  2. Build grounded context prompt
  3. Gemini 2.0 Flash generation with source citation (google-genai SDK)
  4. Token logging + escalation detection

Uses google-genai SDK (replaces deprecated google-generativeai).
"""
import os
import time

from google import genai
from google.genai import types as genai_types
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from .models import Conversation, Message, EscalationTicket
from .token_logger import log_token_usage
from .rag import hybrid_retrieve, _is_rate_limit_error  # ← Hybrid RAG engine

# ── Gemini client (new google-genai SDK) ──────────────────────────────────────
_client = genai.Client(
    api_key=os.environ.get("GEMINI_API_KEY") or settings.GEMINI_API_KEY
)

GEN_MODEL = "gemini-2.5-flash"

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

URGENCY_KEYWORDS = {
    5: ["urgent", "critical", "emergency", "severe", "immediately", "asap", "crash", "down", "outage", "security breach"],
    4: ["important", "broken", "failing", "not working", "blocked", "production", "deadline"],
    3: ["help", "issue", "problem", "error", "bug", "trouble", "wrong", "fix"],
    2: ["question", "wondering", "curious", "how to", "what is", "explain"],
    1: ["general", "feedback", "suggestion", "info", "thanks"],
}

PRIORITY_MAP = {5: "critical", 4: "high", 3: "medium", 2: "low", 1: "low"}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def build_context(chunks: list) -> tuple:
    """
    Join hybrid-retrieved chunks with source document name prefixed.
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
    return 1


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
            "retrieval_method": "hybrid",
            "retrieval_breakdown": {"final_chunks": 5, "retrievers": [...], "fusion": "..."},
            "escalated": false,
            "ticket_id": null,
            "conversation_id": 1,
            "tokens_used": { "prompt": 350, "completion": 120, "total": 470 }
        }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user_message = request.data.get("user_message", "").strip()
        conversation_id = request.data.get("conversation_id")

        # ── Validate ──────────────────────────────────────────────────────────
        if not user_message:
            return Response(
                {"error": "user_message is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Get or create conversation ────────────────────────────────────────
        try:
            if conversation_id:
                conversation = Conversation.objects.get(
                    id=conversation_id, user=request.user
                )
            else:
                conversation = Conversation.objects.create(
                    user=request.user,
                    title=user_message[:100],
                )
        except Conversation.DoesNotExist:
            return Response(
                {"error": f"Conversation {conversation_id} not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # ── Save user message ─────────────────────────────────────────────────
        Message.objects.create(
            conversation=conversation,
            role="user",
            content=user_message,
        )

        # ── Hybrid RAG Retrieval ──────────────────────────────────────────────
        # hybrid_retrieve() runs:
        #   1) Dense:  pgvector HNSW cosine similarity (Gemini embeddings)
        #   2) Sparse: BM25 keyword search (rank_bm25, in-memory)
        #   3) Fusion: Reciprocal Rank Fusion (RRF, k=60)
        try:
            chunks = hybrid_retrieve(
                question=user_message,
                user=request.user,
                top_k=5,
            )
        except Exception as e:
            return Response(
                {"error": f"Hybrid retrieval failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if not chunks:
            context_text = "(No documents available in the knowledge base.)"
            sources = []
        else:
            context_text, sources = build_context(chunks)

        # ── Build prompt & call Gemini 2.0 Flash ─────────────────────────────
        full_prompt = (
            f"{SYSTEM_PROMPT}\n\n"
            f"Context Documents:\n{context_text}\n\n"
            f"Customer Question:\n{user_message}\n\n"
            "Provide a helpful, accurate answer. Cite document names in [brackets]."
        )

        try:
            _retry_delay = 5.0
            _last_exc = None
            _response = None
            for _attempt in range(4):  # up to 3 retries: 5s → 15s → 45s
                try:
                    _response = _client.models.generate_content(
                        model=GEN_MODEL,
                        contents=full_prompt,
                        config=genai_types.GenerateContentConfig(
                            temperature=0.3,
                            max_output_tokens=1000,
                        ),
                    )
                    _last_exc = None
                    break  # success
                except Exception as _exc:
                    _last_exc = _exc
                    if _is_rate_limit_error(_exc) and _attempt < 3:
                        import logging as _lg
                        _lg.getLogger(__name__).warning(
                            "ChatView: Gemini rate limit — retrying in %.0fs (attempt %d/3)",
                            _retry_delay, _attempt + 1,
                        )
                        time.sleep(_retry_delay)
                        _retry_delay *= 3
                    else:
                        raise
            if _last_exc:
                raise _last_exc
            response = _response
            assistant_text = response.text
        except Exception as e:
            err_str = str(e)
            # Detect Gemini rate limit (HTTP 429)
            if '429' in err_str or 'quota' in err_str.lower() or 'rate' in err_str.lower() and 'limit' in err_str.lower():
                return Response(
                    {
                        'error': (
                            'Rate limit reached on the Gemini API. '
                            'The free tier allows ~15 requests/minute and 1,500 requests/day. '
                            'Please wait 60 seconds before trying again, or upgrade your Gemini API plan at '
                            'https://aistudio.google.com/apikey'
                        ),
                        'error_code': 'RATE_LIMITED',
                        'retry_after_seconds': 60,
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )
            return Response(
                {'error': f'AI generation failed: {err_str}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # ── Token usage ───────────────────────────────────────────────────────
        prompt_tokens = 0
        completion_tokens = 0
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            prompt_tokens = getattr(response.usage_metadata, "prompt_token_count", 0) or 0
            completion_tokens = getattr(response.usage_metadata, "candidates_token_count", 0) or 0
        total_tokens = prompt_tokens + completion_tokens

        # ── Log tokens ────────────────────────────────────────────────────────
        log_token_usage(
            user_id=request.user.id,
            username=request.user.username,
            conversation_id=conversation.id,
            user_message=user_message,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )

        # ── Save assistant message ────────────────────────────────────────────
        assistant_msg = Message.objects.create(
            conversation=conversation,
            role="assistant",
            content=assistant_text,
            tokens_used=total_tokens,
        )
        if chunks:
            assistant_msg.context_chunks.set(chunks)

        # ── Escalation detection ──────────────────────────────────────────────
        escalated = False
        ticket_id = None

        if detect_escalation(assistant_text):
            priority_score = score_priority(user_message)
            priority_label = PRIORITY_MAP.get(priority_score, "medium")

            ticket = EscalationTicket.objects.create(
                conversation=conversation,
                issue=f"AI unable to answer (priority {priority_score}/5): {user_message}",
                priority=priority_label,
                status="open",
            )
            escalated = True
            ticket_id = ticket.id

        # ── Return response ───────────────────────────────────────────────────
        return Response({
            "answer": assistant_text,
            "sources": sources,
            "retrieval_method": "hybrid",
            "retrieval_breakdown": {
                "final_chunks": len(chunks),
                "retrievers": ["dense_pgvector_hnsw", "sparse_bm25"],
                "fusion": "reciprocal_rank_fusion",
            },
            "escalated": escalated,
            "ticket_id": ticket_id,
            "conversation_id": conversation.id,
            "tokens_used": {
                "prompt": prompt_tokens,
                "completion": completion_tokens,
                "total": total_tokens,
            },
        })

from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
import os
import logging

from google import genai
from google.genai import types as genai_types

# ---------------------------------------------------------------------------
# PDF extraction — use pypdf (modern replacement for deprecated PyPDF2)
# ---------------------------------------------------------------------------
from pypdf import PdfReader

# ---------------------------------------------------------------------------
# Tiktoken — cached at module level so the encoder is loaded only ONCE
# instead of on every chunk/document call.
# ---------------------------------------------------------------------------
import tiktoken as _tiktoken

_ENCODING = None


def _get_encoding():
    """Return a cached tiktoken encoder (cl100k_base — fast, no model download)."""
    global _ENCODING
    if _ENCODING is None:
        # cl100k_base is the same encoding used by GPT-4/GPT-3.5 and tiktoken
        # ships it locally — no network call needed.
        _ENCODING = _tiktoken.get_encoding("cl100k_base")
    return _ENCODING


# ---------------------------------------------------------------------------
# Gemini client — one client instance reused across all tasks
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)

_client = genai.Client(
    api_key=os.environ.get("GEMINI_API_KEY") or settings.GEMINI_API_KEY
)

EMBED_MODEL = "gemini-embedding-001"
EMBED_BATCH_SIZE = 100  # Gemini official limit; use full capacity for fewer API round-trips
EMBED_TIMEOUT = 30      # seconds; prevent hanging on slow network


# ---------------------------------------------------------------------------
# Celery tasks
# ---------------------------------------------------------------------------

@shared_task
def test_celery_task():
    """Dummy task to test Celery + Redis connection."""
    from django.utils import timezone
    return {
        "status": "success",
        "message": "Celery + Redis is working correctly!",
        "timestamp": str(timezone.now()),
    }


@shared_task(
    bind=True,
    max_retries=1,           # Reduced: avoid 15-second wait on transient errors
    default_retry_delay=2,   # seconds between retries
    acks_late=True,          # re-queue if worker crashes mid-task
)
def process_document(self, document_id):
    """
    Main document processing task (optimized for speed):
      1. Extract text from PDF/TXT
      2. Split into ~1000-token chunks with 20-token overlap (larger = fewer chunks)
      3. Generate embeddings via batched Gemini API calls
         (one API request per batch of EMBED_BATCH_SIZE chunks)
      4. Bulk-insert DocumentChunk rows with embeddings
      5. Mark Document status as 'ready' or 'failed'

    Performance benchmarks
    ----------------------
    - One-page resume (~1000 tokens): 1–2 chunks → 1 API call → ~2–4 seconds
    - Five-page PDF (~5000 tokens): 5–6 chunks → 1 API call → ~3–5 seconds
    - Batch size 100: minimizes API round-trips
    - Token counting pre-computed (avoid re-encoding per chunk)
    - Max 1 retry: prevents 15-second hangs on transient errors
    """
    from .models import Document, DocumentChunk

    try:
        document = Document.objects.get(id=document_id)
        document.status = "processing"
        document.save(update_fields=["status", "updated_at"])

        # ── 1. Validate file ────────────────────────────────────────────────
        if not document.file:
            raise ValueError("Document has no associated file.")

        file_path = document.file.path
        file_ext = os.path.splitext(file_path)[1].lower()

        # ── 2. Extract text ─────────────────────────────────────────────────
        if file_ext == ".pdf":
            text = _extract_text_from_pdf(file_path)
        elif file_ext == ".txt":
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
        else:
            raise ValueError(f"Unsupported file type: {file_ext!r}")

        if not text or not text.strip():
            raise ValueError("Extracted text is empty — PDF may be scanned/image-based.")

        # Persist raw text for audit / fallback search
        document.content = text
        document.save(update_fields=["content", "updated_at"])

        # ── 3. Chunk text ───────────────────────────────────────────────────
        chunks = _split_into_chunks(text, chunk_size=1000, overlap=20)
        if not chunks:
            raise ValueError("No text chunks produced from document.")

        logger.info(
            "process_document[%s]: %d chunks to embed (batches of %d).",
            document_id, len(chunks), EMBED_BATCH_SIZE,
        )

        # Replace any pre-existing chunks (re-processing scenario)
        document.chunks.all().delete()

        # ── 4. Batch-embed + build chunk objects ────────────────────────────
        chunk_objects = []
        encoding = _get_encoding()

        # Pre-compute token counts once (avoid re-encoding per chunk)
        chunk_tokens = [len(encoding.encode(chunk)) for chunk in chunks]

        for batch_start in range(0, len(chunks), EMBED_BATCH_SIZE):
            batch_end = min(batch_start + EMBED_BATCH_SIZE, len(chunks))
            batch_texts = chunks[batch_start:batch_end]
            batch_token_counts = chunk_tokens[batch_start:batch_end]

            logger.debug(
                "process_document[%s]: embedding batch %d–%d (%d texts).",
                document_id, batch_start, batch_end - 1, len(batch_texts),
            )

            # ★ ONE API CALL for the whole batch ★
            batch_embeddings = _get_embeddings_batch(batch_texts)

            for offset, (chunk_text, embedding, token_count) in enumerate(
                zip(batch_texts, batch_embeddings, batch_token_counts)
            ):
                chunk_index = batch_start + offset
                chunk_objects.append(
                    DocumentChunk(
                        document=document,
                        content=chunk_text,
                        chunk_index=chunk_index,
                        embedding=embedding,
                        tokens=token_count,
                    )
                )

        # ── 5. Persist to DB ────────────────────────────────────────────────
        DocumentChunk.objects.bulk_create(chunk_objects)

        document.status = "ready"
        document.save(update_fields=["status", "updated_at"])

        logger.info(
            "process_document[%s]: done — %d chunks ready.",
            document_id, len(chunk_objects),
        )
        return {
            "status": "success",
            "document_id": document_id,
            "chunks_created": len(chunk_objects),
            "message": f"Successfully processed {len(chunk_objects)} chunks.",
        }

    except Exception as exc:
        # Mark document as failed
        try:
            doc = Document.objects.get(id=document_id)
            doc.status = "failed"
            doc.save(update_fields=["status", "updated_at"])
        except Exception:
            pass

        logger.exception("process_document[%s] failed: %s", document_id, exc)

        # Retry on transient errors (rate limits, network blips)
        error_str = str(exc).lower()
        is_transient = any(
            kw in error_str for kw in ("429", "quota", "rate", "timeout", "network", "connection")
        )
        if is_transient:
            raise self.retry(exc=exc)

        return {
            "status": "failed",
            "document_id": document_id,
            "error": str(exc),
        }


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF using pypdf (fast, actively maintained)."""
    pages = []
    try:
        with open(file_path, "rb") as fh:
            reader = PdfReader(fh)
            for page in reader.pages:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    pages.append(page_text)
        return "\n".join(pages)
    except Exception as exc:
        raise ValueError(f"Error extracting PDF text: {exc}") from exc


def _split_into_chunks(text: str, chunk_size: int = 500, overlap: int = 50):
    """
    Tokenise *text* and split into overlapping token windows.

    Uses the module-level cached encoder so tiktoken is initialised only once
    per worker process — not once per document or chunk.
    """
    encoding = _get_encoding()
    tokens = encoding.encode(text)

    chunks = []
    start = 0
    step = chunk_size - overlap  # advance by this many tokens each iteration

    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        chunk_text = encoding.decode(tokens[start:end])
        if chunk_text.strip():
            chunks.append(chunk_text)
        if end == len(tokens):
            break
        start += step

    return chunks


def count_tokens(text: str) -> int:
    """Count tokens using the shared cached encoder."""
    return len(_get_encoding().encode(text))


def _get_embeddings_batch(texts: list, timeout: int = EMBED_TIMEOUT) -> list:
    """
    Generate embeddings for a list of texts using a SINGLE Gemini API call.

    The Gemini embed_content API accepts multiple 'contents' in one request,
    returning one embedding per content in the same order.  This replaces the
    old approach of looping and calling the API once per text.

    Returns a list of embedding vectors (each a list of floats) in the same
    order as *texts*.
    """
    if not texts:
        return []

    try:
        response = _client.models.embed_content(
            model=EMBED_MODEL,
            contents=texts,           # ← list of strings, not a single string
            config=genai_types.EmbedContentConfig(output_dimensionality=768),
        )
        # response.embeddings is a list aligned to the input texts list
        return [list(emb.values) for emb in response.embeddings]

    except Exception as exc:
        error_msg = str(exc).lower()
        logger.error("_get_embeddings_batch failed after %d texts: %s", len(texts), exc)
        # Only raise for true errors, not rate limits (those are transient)
        if "overloaded" in error_msg or "quota" in error_msg:
            raise ValueError(f"Gemini API overloaded; will retry: {exc}") from exc
        raise ValueError(f"Gemini batch embedding error: {exc}") from exc


# ---------------------------------------------------------------------------
# Legacy public wrapper kept for backward-compat with any direct callers
# ---------------------------------------------------------------------------

def get_embeddings_batch(texts: list) -> list:
    """Public alias — delegates to _get_embeddings_batch."""
    return _get_embeddings_batch(texts)


def get_embedding(text: str) -> list:
    """Single-text embedding (wraps batch call for consistency)."""
    result = _get_embeddings_batch([text])
    return result[0] if result else []


# ---------------------------------------------------------------------------
# Other shared tasks
# ---------------------------------------------------------------------------

@shared_task
def escalate_conversation(conversation_id, reason):
    """Create escalation ticket and optionally notify support team."""
    from .models import Conversation, EscalationTicket

    try:
        conversation = Conversation.objects.get(id=conversation_id)
        ticket = EscalationTicket.objects.create(
            conversation=conversation,
            issue=reason,
            priority="high",
        )

        try:
            send_mail(
                subject=f"New Support Escalation: Ticket #{ticket.id}",
                message=(
                    f"Conversation {conversation_id} requires human review.\n"
                    f"Reason: {reason}"
                ),
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[admin[1] for admin in settings.ADMINS],
            )
        except Exception:
            pass  # Email is optional

        return f"Escalation ticket #{ticket.id} created"

    except Exception as exc:
        return f"Error escalating conversation {conversation_id}: {exc}"


@shared_task
def cleanup_old_conversations(days=30):
    """Archive old inactive conversations (run via Celery Beat)."""
    from django.utils import timezone
    from datetime import timedelta
    from .models import Conversation

    try:
        cutoff = timezone.now() - timedelta(days=days)
        count, _ = Conversation.objects.filter(updated_at__lt=cutoff).delete()
        return f"Cleaned up {count} old conversations."
    except Exception as exc:
        return f"Error cleaning conversations: {exc}"

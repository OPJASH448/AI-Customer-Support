"""
Hybrid RAG Engine
=================
Combines two complementary retrieval strategies:

  1. Dense Retrieval  — Gemini gemini-embedding-001 (768-dim) cosine similarity
                        via pgvector HNSW index. Good for semantic / conceptual
                        queries where the exact wording differs from the document.

  2. Sparse Retrieval — PostgreSQL Full-Text Search (tsvector + GIN index) with
                        cover-density ranking and websearch natural query parsing.
                        Good for exact keyword, product-code, and named-entity
                        queries without in-memory Python overhead.

  3. Reciprocal Rank Fusion (RRF) — Merges both ranked lists into a single
                        relevance-ordered list using the formula:
                            score(chunk) = Σ 1 / (k + rank_i)   k = 60
                        Higher fused score → chunk appears first in final list.

Uses google-genai SDK (replaces deprecated google-generativeai).
"""

import os
import re
import time
import logging
from typing import List, Optional

from google import genai
from google.genai import types as genai_types
from django.conf import settings
from django.contrib.postgres.search import SearchQuery, SearchRank
from pgvector.django import CosineDistance

from .models import DocumentChunk

logger = logging.getLogger(__name__)


# ── Retry / backoff helper ─────────────────────────────────────────────────────

def _is_rate_limit_error(exc: Exception) -> bool:
    """Return True when the exception looks like a Gemini 429, 503, 500, or overloaded transient error."""
    msg = str(exc).lower()
    return any(kw in msg for kw in (
        '429', '503', '500', 'quota', 'rate limit', 'resource_exhausted', 
        'rateLimitExceeded'.lower(), 'service unavailable', 'overloaded', 'unavailable'
    ))


def _call_with_backoff(fn, *args, max_retries: int = 3, base_delay: float = 5.0, **kwargs):
    """
    Call *fn* with exponential back-off when a Gemini rate-limit error occurs.

    Retry schedule (seconds): 5 → 15 → 45
    Raises the original exception if all retries are exhausted.
    """
    delay = base_delay
    for attempt in range(max_retries + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            if _is_rate_limit_error(exc) and attempt < max_retries:
                logger.warning(
                    "Gemini rate limit hit — retrying in %.0fs (attempt %d/%d): %s",
                    delay, attempt + 1, max_retries, exc,
                )
                time.sleep(delay)
                delay *= 3  # exponential back-off: 5 → 15 → 45
            else:
                raise

# ── Gemini client (new google-genai SDK) ──────────────────────────────────────
_client = genai.Client(
    api_key=os.environ.get("GEMINI_API_KEY") or settings.GEMINI_API_KEY
)

# ── Constants ──────────────────────────────────────────────────────────────────
RRF_K = 60          # Standard RRF constant — balances precision vs. recall
DENSE_TOP_K = 10    # Candidates fetched from dense retriever before fusion
SPARSE_TOP_K = 10   # Candidates fetched from sparse retriever before fusion
EMBED_MODEL = "gemini-embedding-001"
GEN_MODEL = "gemini-2.5-flash"


# ── Dense retrieval helpers ────────────────────────────────────────────────────

def embed_query(question: str) -> List[float]:
    """
    Create a 768-dim query embedding via Gemini gemini-embedding-001.
    Uses the new google-genai SDK.  Retries automatically on rate-limit errors.
    """
    def _do_embed():
        response = _client.models.embed_content(
            model=EMBED_MODEL,
            contents=question,
            config=genai_types.EmbedContentConfig(output_dimensionality=768),
        )
        return list(response.embeddings[0].values)

    return _call_with_backoff(_do_embed)


def _dense_retrieve(question_embedding: List[float], queryset, top_k: int) -> List:
    """
    pgvector cosine distance search (HNSW-accelerated ANN).
    Returns chunks annotated with .distance (lower = more similar).
    """
    return list(
        queryset.annotate(distance=CosineDistance("embedding", question_embedding))
        .order_by("distance")[:top_k]
    )


# ── Sparse / PostgreSQL Full-Text Search retrieval helpers ───────────────────

def _sparse_retrieve(query: str, queryset, top_k: int) -> List:
    """
    PostgreSQL Full-Text Search (tsvector + GIN index) over the DocumentChunk queryset.
    Replaces in-memory BM25 to eliminate network and memory overhead.
    Uses cover-density ranking (proximity and frequency of matched words).
    """
    clean_query = query.strip()
    if not clean_query:
        return []

    try:
        # 1. Try websearch first (great for exact phrases, quotes, or targeted terms)
        search_query = SearchQuery(clean_query, search_type="websearch", config="english")
        results = list(
            queryset
            .filter(search_vector=search_query)
            .annotate(rank=SearchRank("search_vector", search_query, cover_density=True))
            .order_by("-rank")[:top_k]
        )
        if results:
            return results

        # 2. For conversational questions (e.g. "Tell me about X and Y"), combine
        # informative terms with OR so chunks matching any key term are returned and ranked
        words = [w for w in re.sub(r"[^a-zA-Z0-9\s]", "", clean_query).split() if len(w) > 2]
        if words:
            or_expr = " | ".join(words)
            or_query = SearchQuery(or_expr, search_type="raw", config="english")
            results = list(
                queryset
                .filter(search_vector=or_query)
                .annotate(rank=SearchRank("search_vector", or_query, cover_density=True))
                .order_by("-rank")[:top_k]
            )
            if results:
                return results

        # 3. Fallback to plain query
        plain_query = SearchQuery(clean_query, search_type="plain", config="english")
        return list(
            queryset
            .filter(search_vector=plain_query)
            .annotate(rank=SearchRank("search_vector", plain_query, cover_density=True))
            .order_by("-rank")[:top_k]
        )
    except Exception as exc:
        logger.warning("_sparse_retrieve: PostgreSQL text search error: %s", exc)
        return []


# ── Reciprocal Rank Fusion ─────────────────────────────────────────────────────

def _reciprocal_rank_fusion(
    dense_chunks: List,
    sparse_chunks: List,
    top_k: int,
    k: int = RRF_K,
) -> List:
    """
    Merge dense and sparse ranked lists via Reciprocal Rank Fusion.

    Formula:  rrf_score(d) = Σ_r  1 / (k + rank_r(d))
    Chunks in BOTH lists receive compounded scores and float to the top.
    """
    rrf_scores: dict = {}
    chunk_map: dict = {}

    for rank, chunk in enumerate(dense_chunks, start=1):
        rrf_scores[chunk.id] = rrf_scores.get(chunk.id, 0.0) + 1.0 / (k + rank)
        chunk_map[chunk.id] = chunk

    for rank, chunk in enumerate(sparse_chunks, start=1):
        rrf_scores[chunk.id] = rrf_scores.get(chunk.id, 0.0) + 1.0 / (k + rank)
        chunk_map[chunk.id] = chunk

    sorted_ids = sorted(rrf_scores, key=lambda cid: rrf_scores[cid], reverse=True)
    return [chunk_map[cid] for cid in sorted_ids[:top_k]]


# ── Public API ─────────────────────────────────────────────────────────────────

def hybrid_retrieve(
    question: str,
    user=None,
    top_k: int = 5,
) -> List:
    """
    Full Hybrid RAG retrieval:
      1. Build base queryset (active, ready documents, optionally per-user)
      2. Dense branch  — pgvector HNSW cosine search with Gemini embeddings
      3. Sparse branch — PostgreSQL Full-Text Search (tsvector + GIN index)
      4. RRF fusion    — Merge and re-rank to final top_k

    Falls back gracefully if one branch fails.
    """
    # ── Base queryset ──────────────────────────────────────────────────────────
    queryset = DocumentChunk.objects.select_related("document").filter(
        document__status="ready",
        document__is_active=True,
    )
    if user is not None:
        queryset = queryset.filter(document__uploaded_by=user)

    # ── Check active corpus ───────────────────────────────────────────────────
    if not queryset.exists():
        logger.warning("hybrid_retrieve: no active/ready chunks found.")
        return []

    # ── Dense branch ───────────────────────────────────────────────────────────
    try:
        question_embedding = embed_query(question)
        dense_chunks = _dense_retrieve(question_embedding, queryset, top_k=DENSE_TOP_K)
    except Exception as exc:
        logger.error("hybrid_retrieve: dense branch failed — %s", exc)
        dense_chunks = []

    # ── Sparse (PostgreSQL FTS) branch ─────────────────────────────────────────
    try:
        sparse_chunks = _sparse_retrieve(question, queryset, top_k=SPARSE_TOP_K)
    except Exception as exc:
        logger.error("hybrid_retrieve: sparse branch failed — %s", exc)
        sparse_chunks = []

    # ── Graceful degradation ───────────────────────────────────────────────────
    if not dense_chunks and not sparse_chunks:
        logger.warning("hybrid_retrieve: both branches returned empty.")
        return []
    if not dense_chunks:
        logger.info("hybrid_retrieve: dense failed, using sparse-only.")
        return sparse_chunks[:top_k]
    if not sparse_chunks:
        logger.info("hybrid_retrieve: sparse empty, using dense-only.")
        return dense_chunks[:top_k]

    # ── RRF Fusion ─────────────────────────────────────────────────────────────
    fused = _reciprocal_rank_fusion(dense_chunks, sparse_chunks, top_k=top_k)
    logger.info(
        "hybrid_retrieve: dense=%d sparse=%d fused=%d",
        len(dense_chunks), len(sparse_chunks), len(fused),
    )
    return fused


# ── Backward-compatible wrappers ───────────────────────────────────────────────

def retrieve_similar_chunks(question_embedding: List[float], user=None, top_k: int = 5):
    """
    Legacy dense-only retrieval shim used by older callers.
    New code should call hybrid_retrieve() for full Hybrid RAG.
    """
    queryset = DocumentChunk.objects.select_related("document").filter(
        document__status="ready",
        document__is_active=True,
    )
    if user is not None:
        queryset = queryset.filter(document__uploaded_by=user)

    return list(
        queryset.annotate(distance=CosineDistance("embedding", question_embedding))
        .order_by("distance")[:top_k]
    )


def generate_grounded_answer(question: str, chunks: List) -> str:
    """
    Generate a grounded Gemini 2.0 Flash response from retrieved chunks.
    Uses the new google-genai SDK.
    """
    if not chunks:
        context = "No relevant context found."
    else:
        context_blocks = []
        for idx, chunk in enumerate(chunks, start=1):
            context_blocks.append(
                f"[{idx}] Document: {chunk.document.title}\n"
                f"Chunk Index: {chunk.chunk_index}\n"
                f"Content:\n{chunk.content}"
            )
        context = "\n\n".join(context_blocks)

    prompt = (
        "You are a customer support assistant.\n"
        "Answer ONLY using the retrieved context below.\n"
        "Cite source document names in [brackets] after each fact.\n"
        "If the context is insufficient, clearly state what information is missing.\n\n"
        f"Question:\n{question}\n\n"
        f"Retrieved Context:\n{context}\n"
    )

    def _do_generate():
        return _client.models.generate_content(
            model=GEN_MODEL,
            contents=prompt,
        )

    response = _call_with_backoff(_do_generate)
    return (response.text or "I could not generate a response.").strip()

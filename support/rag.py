import os
from typing import List

import google.generativeai as genai
from django.conf import settings
from pgvector.django import CosineDistance

from .models import DocumentChunk


genai.configure(api_key=os.environ.get('GEMINI_API_KEY') or settings.GEMINI_API_KEY)


def embed_query(question: str) -> List[float]:
    """Create a 768-dim query embedding with Gemini."""
    result = genai.embed_content(
        model="models/gemini-embedding-001",
        content=question,
        output_dimensionality=768,
    )
    return result["embedding"]


def retrieve_similar_chunks(question_embedding: List[float], user=None, top_k: int = 5):
    """
    Retrieve nearest chunks using cosine distance.
    With HNSW index in pgvector, this ORDER BY query is ANN-accelerated.
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


def generate_grounded_answer(question: str, chunks: List[DocumentChunk]) -> str:
    """Generate final response using retrieved chunks as grounding context."""
    context_blocks = []
    for idx, chunk in enumerate(chunks, start=1):
        context_blocks.append(
            f"[{idx}] Document: {chunk.document.title}\n"
            f"Chunk Index: {chunk.chunk_index}\n"
            f"Content:\n{chunk.content}"
        )

    context = "\n\n".join(context_blocks) if context_blocks else "No relevant context found."

    prompt = (
        "You are a customer support assistant.\n"
        "Answer ONLY using the retrieved context.\n"
        "If context is insufficient, clearly say what is missing.\n\n"
        f"Question:\n{question}\n\n"
        f"Retrieved Context:\n{context}\n"
    )

    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(prompt)
    return (response.text or "I could not generate a response.").strip()

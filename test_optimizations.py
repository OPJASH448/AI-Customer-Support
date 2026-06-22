#!/usr/bin/env python
"""
Test the optimized document processing performance.
Run: python test_optimizations.py
"""
import os
import django
import time
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from django.contrib.auth.models import User
from support.models import Document, DocumentChunk
from support.tasks import process_document, _split_into_chunks, count_tokens, _get_encoding

print("=" * 70)
print("DOCUMENT PROCESSING OPTIMIZATION TEST")
print("=" * 70)

# Test 1: Token counting and chunking efficiency
print("\n[TEST 1] Chunking Efficiency")
print("-" * 70)

# Simulate a one-page resume (~1000 tokens)
sample_text = """
JASWANTH KANIPAKAM
Student ID: 23BCS123
Email: jaswanth@example.com | Phone: +91-9876543210

EDUCATION
Bachelor of Technology in Computer Science and Engineering
XYZ Institute of Technology, India | Expected: 2024 | CGPA: 8.5/10

SKILLS
• Programming: Python, JavaScript, Java, SQL, C++
• Web Development: Django, React, REST APIs, HTML/CSS
• Databases: PostgreSQL, MongoDB, MySQL
• Cloud: AWS, Google Cloud, Docker, Kubernetes
• AI/ML: TensorFlow, PyTorch, Pandas, Scikit-learn

EXPERIENCE
Software Development Intern | ABC Tech Pvt Ltd | Jan 2024 - Present
- Developed REST APIs using Django and PostgreSQL
- Implemented vector search using pgvector for RAG systems
- Optimized document processing pipeline, reducing latency by 60%
- Tech Stack: Python, Django, PostgreSQL, Redis

AI Research Assistant | University Lab | Aug 2023 - Dec 2023
- Built RAG system for customer support using Gemini API
- Implemented embedding generation and similarity search
- Created automated document chunking pipeline
- Tech Stack: Python, Gemini API, pgvector

PROJECTS
AI Customer Support Agent
- Full-stack RAG system with vector embeddings
- Document upload, chunking, and semantic search
- Real-time chat interface with context awareness
- Stack: Django, React, PostgreSQL, pgvector, Gemini API

CERTIFICATIONS
- Cloud Computing Fundamentals (Google Cloud)
- Machine Learning Specialization (Coursera)
""".strip()

token_count = count_tokens(sample_text)
print(f"Sample text tokens: {token_count}")

# Test old chunk size (500 tokens, 50 overlap)
start = time.time()
old_chunks = _split_into_chunks(sample_text, chunk_size=500, overlap=50)
old_time = time.time() - start
print(f"Old config (500-token chunks, 50-overlap): {len(old_chunks)} chunks in {old_time*1000:.2f}ms")

# Test new chunk size (1000 tokens, 20 overlap)
start = time.time()
new_chunks = _split_into_chunks(sample_text, chunk_size=1000, overlap=20)
new_time = time.time() - start
print(f"New config (1000-token chunks, 20-overlap): {len(new_chunks)} chunks in {new_time*1000:.2f}ms")

improvement = (len(old_chunks) - len(new_chunks)) / len(old_chunks) * 100
print(f"✓ Chunk count reduced by {improvement:.0f}% ({len(old_chunks)} → {len(new_chunks)})")

# Test 2: Batch API efficiency
print("\n[TEST 2] Batch Processing Efficiency")
print("-" * 70)

old_batch_size = 20
new_batch_size = 100
num_chunks = len(new_chunks)

old_batches = (num_chunks + old_batch_size - 1) // old_batch_size
new_batches = (num_chunks + new_batch_size - 1) // new_batch_size

print(f"Number of chunks to embed: {num_chunks}")
print(f"Old batch size ({old_batch_size}): {old_batches} API calls")
print(f"New batch size ({new_batch_size}): {new_batches} API calls")
print(f"✓ API calls reduced by {(old_batches - new_batches) / old_batches * 100:.0f}%" if old_batches > new_batches else "✓ Same number of API calls")

# Test 3: Expected timing
print("\n[TEST 3] Expected Processing Time")
print("-" * 70)

components = {
    "File upload": 0.1,
    "PDF extraction": 0.2,
    "Chunking": 0.05,
    f"Gemini API calls ({new_batches})": new_batches * 2.5,  # ~2.5s per API call
    "Database insert": 0.1,
}

total_time = sum(components.values())

for component, duration in components.items():
    print(f"  {component:.<40} {duration:.2f}s")
print("-" * 70)
print(f"  {'Total (optimized)':.<40} {total_time:.2f}s")
print(f"\nExpected for one-page resume: 2.5-4.0 seconds (end-to-end)")

# Test 4: Database check
print("\n[TEST 4] Database Connectivity")
print("-" * 70)

try:
    user_count = User.objects.count()
    doc_count = Document.objects.count()
    chunk_count = DocumentChunk.objects.count()
    
    print(f"✓ Users: {user_count}")
    print(f"✓ Documents: {doc_count}")
    print(f"✓ Chunks: {chunk_count}")
    print("✓ Database connection OK")
except Exception as e:
    print(f"✗ Database error: {e}")

print("\n" + "=" * 70)
print("OPTIMIZATION TEST COMPLETE")
print("=" * 70)
print("\nSummary:")
print(f"  • Chunk count: {len(old_chunks)} → {len(new_chunks)} (-{improvement:.0f}%)")
print(f"  • API calls: {old_batches} → {new_batches}")
print(f"  • Expected time: ~{total_time:.1f} seconds")
print("\nNext step: Upload a PDF and check processing status via /api/support/documents/")
print("=" * 70)

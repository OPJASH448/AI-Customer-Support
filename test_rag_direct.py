#!/usr/bin/env python
"""
Direct RAG retrieval without LLM - shows matching document chunks for a query.
"""
import os

# SET API KEY BEFORE IMPORTING ANYTHING DJANGO/GOOGLE
# Key is loaded from GEMINI_API_KEY env var (set in .env or environment)
if not os.environ.get('GEMINI_API_KEY'):
    raise EnvironmentError("GEMINI_API_KEY not set. Add it to your .env file.")

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from django.contrib.auth.models import User
from support.models import Document, DocumentChunk
from support.rag import hybrid_retrieve

# Get the user 'jas'
user = User.objects.filter(username='jas').first()
if not user:
    print('❌ User "jas" not found')
    exit(1)

print(f"✓ Logged in as: {user.username}")

# Get user's documents
docs = Document.objects.filter(uploaded_by=user, status='ready')
print(f'✓ Found {docs.count()} ready documents\n')

if docs.count() == 0:
    print('❌ No ready documents found. Check document status.')
    all_docs = Document.objects.filter(uploaded_by=user)
    for doc in all_docs:
        print(f"  - {doc.title}: {doc.status} ({doc.chunks.count()} chunks)")
    exit(1)

# List documents
print("Documents:")
for doc in docs:
    print(f"  • {doc.title}: {doc.chunks.count()} chunks")

# Query for achievements WITHOUT LLM
query = "what are the achievements of jaswanth"
print(f'\n{"=" * 80}')
print(f'QUERY: "{query}"')
print("=" * 80)

print('\n[STEP 1] Generating query embedding...')
print('[STEP 2] Searching document chunks with vector similarity (HNSW)...')
print('[STEP 3] Returning top-k chunks WITHOUT LLM generation...\n')

# Use RAG retrieval WITHOUT LLM
results = hybrid_retrieve(query, user=user, top_k=5)

print(f'✓ Retrieved {len(results)} relevant chunks:\n')

if not results:
    print('❌ No relevant chunks found.')
    exit(1)

for i, chunk in enumerate(results, 1):
    chunk_id = chunk.id
    content = chunk.content
    
    print(f'\n{"=" * 80}')
    print(f'[CHUNK {i}]')
    print(f'Chunk ID: {chunk_id}')
    print(f'Document: {chunk.document.title}')
    print("=" * 80)
    print(content)

print(f'\n{"=" * 80}')
print('✓ RAG RETRIEVAL COMPLETE')
print('✓ NO LLM API CALLS MADE - Direct document retrieval only')
print(f'✓ Total chunks retrieved: {len(results)}')
print("=" * 80)

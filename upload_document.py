"""Upload and process opp.txt into the RAG knowledge base."""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from support.models import Document, DocumentChunk
from support.tasks import process_document

# Source file
FILE_PATH = r"C:\Users\kanip\OneDrive\Documents\opp.txt"

# Read the file
print(f"Reading file: {FILE_PATH}")
with open(FILE_PATH, 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()
print(f"File size: {len(content)} characters")

# Get user
user = User.objects.get(username='testuser')
print(f"User: {user.username} (id={user.id})")

# Clean up old processing-stuck documents
stuck = Document.objects.filter(status='processing')
if stuck.count() > 0:
    print(f"Cleaning up {stuck.count()} stuck documents...")
    stuck.delete()

# Create document with file
print("Creating document...")
doc = Document.objects.create(
    title="opp.txt - Robot Controller Code",
    source="local_upload",
    uploaded_by=user,
    status='processing',
    content=content,
)

# Save the file to media
from django.core.files.base import ContentFile
file_content = content.encode('utf-8')
doc.file.save('opp.txt', ContentFile(file_content), save=True)
print(f"Document created: id={doc.id}, title={doc.title}")

# Process document (chunk + embed)
print("Processing document (chunking + embedding)...")
print("This calls Gemini API for embeddings - may take a moment...")
result = process_document(doc.id)
print(f"Result: {result}")

# Verify
doc.refresh_from_db()
chunk_count = doc.chunks.count()
print(f"\nFinal status: {doc.status}")
print(f"Chunks created: {chunk_count}")

if chunk_count > 0:
    print("\nSample chunks:")
    for chunk in doc.chunks.all()[:3]:
        preview = chunk.content[:100].replace('\n', ' ')
        print(f"  Chunk {chunk.chunk_index}: [{chunk.tokens} tokens] {preview}...")
    print(f"\n✅ Document ready for RAG queries!")
else:
    print("\n❌ No chunks created - check for errors above")

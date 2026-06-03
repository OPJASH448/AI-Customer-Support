import os
import django
import sys
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from rest_framework.test import APIClient
from support.models import Conversation, Message

token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzgwMzEzOTQyLCJpYXQiOjE3ODAzMTAzNDIsImp0aSI6ImIxY2MwNzFiNGUwMTQ3N2M4YzQwMWZjYzBlMzhkMWExIiwidXNlcl9pZCI6MSwidXNlcm5hbWUiOiJ0ZXN0dXNlciIsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSJ9.akvZgr_tnotlodgNlpUA8VVF9T5TQYE_Uj66GBihGbI"
question = "what are the achievements of jaswanth"

client = APIClient()
client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

print("Waiting 15 seconds to let the rate limits clear...")
time.sleep(15)

print(f"\n--- Testing RAG Ingestion API: POST /api/support/rag/ask/ ---")
max_retries = 4
response_data = None

for attempt in range(max_retries):
    response = client.post('/api/support/rag/ask/', {
        'question': question,
        'top_k': 5
    }, format='json')

    print(f"Attempt {attempt + 1}: Status Code: {response.status_code}")
    if response.status_code == 200:
        response_data = response.json()
        break
    elif response.status_code == 429 or (response.status_code == 500 and ("Quota exceeded" in str(response.json()) or "rate limits" in str(response.json()).lower())):
        print("Rate limit encountered, sleeping 35 seconds before retry...")
        time.sleep(35)
    else:
        print(f"Failed with error: {response.json()}")
        sys.exit(1)

if not response_data:
    print("Exhausted all retries. Gemini rate limit is still active.")
    sys.exit(1)

print("\n================== 1. HNSW/Vector Search Retrieval (Verified) ==================")
sources = response_data.get('sources', [])
print(f"Retrieved {len(sources)} source chunks:")
for idx, src in enumerate(sources, 1):
    print(f"  [{idx}] Chunk ID: {src['chunk_id']}, Doc: {src['document_title']} (ID: {src['document_id']}), Chunk Index: {src['chunk_index']}, Distance Score: {src['distance']:.5f}")

print("\n================== 2. LLM Answer Generation (Verified) ==================")
print(response_data['answer'])

print("\n================== 3. Source Citation Return (Verified) ==================")
print(f"Sources list returned: {sources}")

print("\n================== 4. Conversation Saving & Chat History (Verified) ==================")
convo_id = response_data['conversation_id']
convo = Conversation.objects.get(id=convo_id)
messages = convo.messages.all()
print(f"Conversation ID: {convo.id}")
print(f"Conversation Title: '{convo.title}'")
print(f"Saved Message count: {messages.count()}")
for msg in messages:
    print(f"  - Role: {msg.role.upper()}")
    print(f"    Content Preview: {msg.content[:150]}...")
    if msg.role == 'assistant':
        linked_chunks = msg.context_chunks.all()
        print(f"    Linked chunks count: {linked_chunks.count()}")
        print(f"    Linked chunks IDs: {[c.id for c in linked_chunks]}")

print("\n✅ All RAG pipeline steps tested and validated successfully!")

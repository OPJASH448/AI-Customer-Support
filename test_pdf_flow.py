import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from rest_framework.test import APIClient
from django.contrib.auth.models import User
from support.models import Document, DocumentChunk
from support.tasks import process_document

token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzgwMzEzOTQyLCJpYXQiOjE3ODAzMTAzNDIsImp0aSI6ImIxY2MwNzFiNGUwMTQ3N2M4YzQwMWZjYzBlMzhkMWExIiwidXNlcl9pZCI6MSwidXNlcm5hbWUiOiJ0ZXN0dXNlciIsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSJ9.akvZgr_tnotlodgNlpUA8VVF9T5TQYE_Uj66GBihGbI"
pdf_path = r"C:\Users\kanip\Downloads\JaswanthKanipakam.23BCS123.pdf"

print("--- Step 1: Initializing APIClient with JWT Token ---")
client = APIClient()
client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

print(f"--- Step 2: Uploading PDF to /api/support/documents/ ---")
if not os.path.exists(pdf_path):
    print(f"Error: File {pdf_path} does not exist.")
    sys.exit(1)

with open(pdf_path, 'rb') as f:
    response = client.post('/api/support/documents/', {
        'title': 'Jaswanth Kanipakam CV',
        'source': 'local_upload',
        'file': f
    }, format='multipart')

print(f"Upload Response Status Code: {response.status_code}")
if response.status_code not in [200, 201]:
    print(f"Upload failed: {response.json()}")
    sys.exit(1)

data = response.json()
print("Upload success details:")
print(data)

doc_id = data['document']['id']
print(f"\n--- Step 3: Processing Document ID {doc_id} (Chunking & Embedding) ---")
task_result = process_document(doc_id)
print(f"Task result: {task_result}")

doc = Document.objects.get(id=doc_id)
print(f"Document Status after processing: {doc.status}")
print(f"Document Chunk Count: {doc.chunks.count()}")

print(f"\n--- Step 4: Asking Chat View: 'what are the achievements of jaswanth' ---")
chat_response = client.post('/api/chat/', {
    'user_message': 'what are the achievements of jaswanth'
}, format='json')

print(f"Chat Response Status Code: {chat_response.status_code}")
if chat_response.status_code != 200:
    print(f"Chat failed: {chat_response.json()}")
    sys.exit(1)

chat_data = chat_response.json()
print("\n================== CHAT ANSWER ==================")
print(chat_data['answer'])
print("=================================================")
print("\nSources Cited:")
print(chat_data['sources'])

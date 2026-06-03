import os
import django
import sys
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from rest_framework.test import APIClient

token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzgwMzEzOTQyLCJpYXQiOjE3ODAzMTAzNDIsImp0aSI6ImIxY2MwNzFiNGUwMTQ3N2M4YzQwMWZjYzBlMzhkMWExIiwidXNlcl9pZCI6MSwidXNlcm5hbWUiOiJ0ZXN0dXNlciIsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSJ9.akvZgr_tnotlodgNlpUA8VVF9T5TQYE_Uj66GBihGbI"

client = APIClient()
client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

print("Waiting 15 seconds to let the rate limit reset...")
time.sleep(15)

print("\n--- Asking Chat View: 'what are the achievements of jaswanth' ---")
max_retries = 3
for attempt in range(max_retries):
    chat_response = client.post('/api/chat/', {
        'user_message': 'what are the achievements of jaswanth'
    }, format='json')

    print(f"Attempt {attempt + 1}: Chat Response Status Code: {chat_response.status_code}")
    if chat_response.status_code == 200:
        chat_data = chat_response.json()
        print("\n================== CHAT ANSWER ==================")
        print(chat_data['answer'])
        print("=================================================")
        print("\nSources Cited:")
        print(chat_data['sources'])
        sys.exit(0)
    elif chat_response.status_code == 500 and "Quota exceeded" in str(chat_response.json()):
        print(f"Quota exceeded, waiting 15 seconds and retrying...")
        time.sleep(15)
    else:
        print(f"Chat failed: {chat_response.json()}")
        sys.exit(1)

print("Exhausted retries due to Gemini rate limits.")

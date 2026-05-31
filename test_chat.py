"""Test script for the RAG Chat endpoint."""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

import json
import requests
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from support.models import Conversation, Message, EscalationTicket
from support.token_logger import get_token_summary

def run_tests():
    # 1. Get testuser
    try:
        user = User.objects.get(username='testuser')
    except User.DoesNotExist:
        print("❌ 'testuser' does not exist in the database.")
        return

    # 2. Generate JWT access token
    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)
    print(f"[SUCCESS] Generated JWT Access Token for {user.username}")

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    # 3. Test Case 1: Knowledge-based Query (RAG success)
    print("\n--- Test Case 1: Knowledge-based Query ---")
    data1 = {
        "user_message": "How does the robot detect plants? Explain the code and pin configuration."
    }
    
    try:
        r1 = requests.post('http://localhost:8000/api/chat/', json=data1, headers=headers)
        print(f"Status Code: {r1.status_code}")
        response_data1 = r1.json()
        print("Response JSON:")
        print(json.dumps(response_data1, indent=2))
        
        conversation_id = response_data1.get('conversation_id')
    except Exception as e:
        print(f"[FAIL] Test Case 1 request failed: {e}")
        return

    # 4. Test Case 2: Out of scope Query (Triggers 'I don't know' and escalation)
    print("\n--- Test Case 2: Out-of-scope Query (Escalation) ---")
    data2 = {
        "user_message": "What is the capital of France?",
        "conversation_id": conversation_id
    }
    
    try:
        r2 = requests.post('http://localhost:8000/api/chat/', json=data2, headers=headers)
        print(f"Status Code: {r2.status_code}")
        response_data2 = r2.json()
        print("Response JSON:")
        print(json.dumps(response_data2, indent=2))
    except Exception as e:
        print(f"[FAIL] Test Case 2 request failed: {e}")
        return

    # 5. Database Verification
    print("\n--- Database & Logs Verification ---")
    conv = Conversation.objects.get(id=conversation_id)
    messages = Message.objects.filter(conversation=conv).order_by('created_at')
    print(f"Conversation Title: '{conv.title}'")
    print(f"Total Messages in Conversation: {messages.count()}")
    for idx, msg in enumerate(messages):
        print(f"  {idx+1}. [{msg.role.upper()}]: {msg.content[:150]}...")
        if msg.context_chunks.count() > 0:
            print(f"     (Linked Context Chunks: {msg.context_chunks.count()})")

    tickets = EscalationTicket.objects.filter(conversation=conv)
    print(f"\nEscalation Tickets for this Conversation: {tickets.count()}")
    for ticket in tickets:
        print(f"  - Ticket ID {ticket.id}: '{ticket.issue}' | Priority: {ticket.priority} | Status: {ticket.status}")

    # 6. Token Log Verification
    summary = get_token_summary()
    print(f"\nToken Log Summary:")
    print(f"  Total Requests: {summary['total_requests']}")
    print(f"  Total Tokens Used: {summary['total_tokens']}")
    if summary['records']:
        print("  Latest Log Record:")
        print(json.dumps(summary['records'][-1], indent=2))

if __name__ == '__main__':
    run_tests()

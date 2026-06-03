import os
import django
import sys
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

import google.generativeai as genai
from support.models import Document, DocumentChunk

# Configure Gemini
genai.configure(api_key=os.environ.get('GEMINI_API_KEY') or "AIzaSy...")

print("--- Step 1: Retrieving HNSW Indexed Chunks from DB ---")
doc = Document.objects.get(id=13)
chunks = list(doc.chunks.all().order_by('chunk_index'))

print(f"Retrieved {len(chunks)} chunks for document '{doc.title}':")
for c in chunks:
    print(f"  - Chunk {c.chunk_index} ({c.tokens} tokens)")

print("\n--- Step 2: Formulating Grounded Context Prompt ---")
context_blocks = []
for idx, chunk in enumerate(chunks, start=1):
    context_blocks.append(
        f"[{idx}] Document: {chunk.document.title}\n"
        f"Chunk Index: {chunk.chunk_index}\n"
        f"Content:\n{chunk.content}"
    )

context = "\n\n".join(context_blocks)
question = "what are the achievements of jaswanth"

system_prompt = (
    "You are an AI customer support agent. Answer questions ONLY based on the provided context documents.\n"
    "Rules:\n"
    "1. ONLY use information from the provided context to answer the question.\n"
    "2. Cite your sources by putting the document name in [brackets] after each claim.\n"
    "3. Be helpful, concise, and accurate.\n"
    "4. Never fabricate information that is not present in the context."
)

user_prompt = f"""Context Documents:
{context}

Customer Question:
{question}

Provide a helpful, accurate answer. Cite document names in [brackets]."""

prompt_payload = f"{system_prompt}\n\n{user_prompt}"

print("\n--- Step 3: Dispatching to Gemini 2.0 Flash with Exponential Backoff ---")
model = genai.GenerativeModel('gemini-2.0-flash')

backoffs = [15, 30, 45, 60]
success = False
answer = ""

for attempt, delay in enumerate(backoffs):
    try:
        print(f"Attempt {attempt + 1}: Calling Gemini API...")
        response = model.generate_content(
            prompt_payload,
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,
                max_output_tokens=1000,
            )
        )
        answer = response.text
        success = True
        print("Success!")
        break
    except Exception as e:
        print(f"Error on attempt {attempt + 1}: {str(e)}")
        if "quota" in str(e).lower() or "429" in str(e):
            print(f"Rate limited. Sleeping {delay} seconds...")
            time.sleep(delay)
        else:
            print("Non-rate-limit failure. Exiting.")
            sys.exit(1)

if not success:
    print("Failed to clear rate limits after multiple backoffs.")
    sys.exit(1)

print("\n================== LLM GENERATED GROUNDED ANSWER ==================")
print(answer)
print("====================================================================")

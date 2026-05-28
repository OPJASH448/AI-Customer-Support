# Development Checklist - Day 1 to Launch

## Pre-Setup (Before Running Anything)

- [ ] Clone project and navigate to directory
- [ ] Create Python virtual environment: `python -m venv venv`
- [ ] Activate venv (Windows: `venv\Scripts\activate` | Unix: `source venv/bin/activate`)
- [ ] Install dependencies: `pip install -r requirements.txt`

## Local Setup

- [ ] Copy `.env.example` to `.env`
- [ ] Generate SECRET_KEY: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
- [ ] Update `.env` with:
  - `SECRET_KEY=<generated-key>`
  - `DATABASE_URL=postgresql://postgres:postgres@localhost/customer_support`
  - `REDIS_URL=redis://localhost:6379/0`
  - `OPENAI_API_KEY=<your-api-key>`

## Database Setup

- [ ] Ensure PostgreSQL is running locally
- [ ] Create database: `createdb -U postgres customer_support`
- [ ] Run migrations: `python manage.py migrate`
- [ ] Create admin: `python manage.py createsuperuser`
- [ ] Verify setup: `python manage.py check`

## Test Locally

- [ ] Start Django: `python manage.py runserver` (Terminal 1)
- [ ] Start Celery: `celery -A config worker --loglevel=info` (Terminal 2)
- [ ] Access: http://localhost:8000/admin
- [ ] Create test user and log in
- [ ] Verify no console errors

## Before First GitHub Push

- [ ] Run `python manage.py check --deploy` for production readiness
- [ ] Test: `python manage.py collectstatic --noinput` (should work)
- [ ] Verify `.gitignore` covers `__pycache__`, `.env`, `venv/`, `*.pyc`
- [ ] Create `.git/config` with proper remote URL

## GitHub & Render Setup

- [ ] Initialize git: `git init`
- [ ] Add all files: `git add .`
- [ ] First commit: `git commit -m "Initial: Django scaffold with RAG"`
- [ ] Create GitHub repo and add remote: `git remote add origin <repo-url>`
- [ ] Push main branch: `git push -u origin main`
- [ ] Go to https://render.com and create account
- [ ] Connect GitHub account to Render
- [ ] Create new Web Service: select this GitHub repo
- [ ] Render auto-detects `render.yaml` - verify settings
- [ ] Review environment variables in Render dashboard
- [ ] Deploy!

## Post-Deployment (Render Dashboard Shell)

- [ ] Run migrations: `python manage.py migrate`
- [ ] Create production admin: `python manage.py createsuperuser`
- [ ] Test production URL in browser
- [ ] Monitor logs for errors

## Feature Development (Week 1-2)

### Core API Endpoints
- [ ] `/api/support/documents/` - Upload knowledge base docs
- [ ] `/api/support/conversations/` - Create/list conversations
- [ ] `/api/support/messages/` - Send message, get RAG response
- [ ] `/api/support/escalate/` - Create escalation ticket

### Frontend (HTMX + Tailwind)
- [ ] Chat interface in `templates/chat.html`
- [ ] Document upload form
- [ ] Admin escalation dashboard
- [ ] Responsive design with Tailwind

### RAG Pipeline
- [ ] Implement document chunking logic
- [ ] Hook up OpenAI embeddings
- [ ] Test vector search with pgvector
- [ ] Integrate with conversation API

## Performance & Monitoring

- [ ] Set up logging to track errors
- [ ] Monitor Celery task queue in Render
- [ ] Track token usage for cost management
- [ ] Set rate limiting for API endpoints

## Security Review (Before Demo)

- [ ] Rotate SECRET_KEY for production
- [ ] Verify HTTPS enforcement in production
- [ ] Test CORS headers are correct
- [ ] Ensure API authentication is working
- [ ] Check for SQL injection vulnerabilities
- [ ] Review database backups strategy on Render

## Interview Demo Script

1. **Start**: "This is an AI Customer Support Agent with RAG vector search"
2. **Show**: Django admin with Document, DocumentChunk, Conversation models
3. **Explain**: "Each document is embedded into 1536-dim vectors via OpenAI and stored in pgvector"
4. **Demo**: Upload a document, send a query
5. **Walk through**: How RAG retrieves similar chunks, augments the prompt, gets AI response
6. **Show**: Async task processing with Celery
7. **End**: "Everything deploys to Render via `git push` - zero manual DevOps"

---

**Timeline**: Complete all checklist items = Day 1 Ready  
**Goal**: By end of week 1, have working RAG pipeline with UI

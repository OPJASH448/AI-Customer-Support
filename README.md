# AI Customer Support Agent

A production-ready Django application for an AI-powered customer support system with RAG (Retrieval Augmented Generation) vector search, built for Render deployment.

## 🚀 Features

- **RAG-Powered Search**: Vector embeddings with pgvector for semantic document search
- **Multi-turn Conversations**: Track conversations and escalations
- **OpenAI Integration**: Powered by GPT models for intelligent responses
- **Celery Workers**: Async task processing (embeddings, escalations)
- **Production Settings**: Environment-aware configuration for local/production
- **Render-Ready**: render.yaml configured for Day 1 deployment

## 📋 Project Structure

```
config/
  settings/
    - base.py        (shared configuration)
    - local.py       (development)
    - production.py  (Render deployment)
  wsgi.py
  asgi.py
  urls.py
  celery.py

support/              (Core support app)
  models.py           (Document, DocumentChunk, Conversation, Message, EscalationTicket)
  views.py
  admin.py

accounts/             (User management)
  models.py           (UserProfile)
  views.py
  admin.py

requirements.txt      (All dependencies)
render.yaml          (Render deployment config)
.env.example         (Environment variables template)
manage.py
```

## 🔧 Setup Instructions

### 1. Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Update .env with local settings (PostgreSQL + Redis)
# DATABASE_URL=postgresql://postgres:postgres@localhost:5432/customer_support
# REDIS_URL=redis://localhost:6379/0

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Start development server
python manage.py runserver

# In another terminal, start Celery worker
celery -A config worker --loglevel=info
```

### 2. Deploy to Render

```bash
# 1. Push code to GitHub
git init
git add .
git commit -m "Initial commit: Django scaffold"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/AI-Customer-Support.git
git push -u origin main

# 2. Go to https://render.com and connect repository
# 3. Render will auto-detect render.yaml and deploy

# 4. After deployment, run migrations
# Visit Render dashboard → select service → Shell
# python manage.py migrate
# python manage.py createsuperuser
```

## 📦 Key Dependencies

- **Django 4.2**: Web framework
- **djangorestframework**: REST API
- **pgvector**: PostgreSQL vector search
- **Celery + Redis**: Async task processing
- **gunicorn**: Production WSGI server
- **whitenoise**: Static files serving
- **django-environ + dj-database-url**: Configuration management
- **OpenAI**: LLM integration

## 🗄️ Database Models

### Document
- `title`, `content`, `source`
- Uploaded documents for knowledge base

### DocumentChunk
- Vector embeddings (pgvector, 1536 dims)
- Split documents for RAG search
- Token counts for cost tracking

### Conversation
- User-to-AI chat history
- Active/inactive tracking

### Message
- Individual messages with role (user/assistant)
- Context chunks used for response

### EscalationTicket
- Issues requiring human review
- Priority levels and assignment

## 🎯 RAG Implementation Notes

1. **Embedding**: Documents → chunks → OpenAI embeddings → pgvector storage
2. **Retrieval**: User query → embedding → pgvector similarity search
3. **Augmentation**: Top-K chunks → context window → OpenAI completion
4. **Interview Impact**: Demonstrate end-to-end RAG workflow

## 🔐 Security

- `SECURE_SSL_REDIRECT = True` in production
- JWT authentication ready
- CORS configured
- Environment variables for secrets

## 📚 Next Steps

1. Build document upload endpoint
2. Implement OpenAI embedding + retrieval
3. Create conversation API endpoints
4. Add HTMX frontend
5. Deploy to Render with `git push`

## 📝 Environment Variables

See `.env.example`. Key variables:

```
SECRET_KEY              - Django secret (generate new in production)
DATABASE_URL            - PostgreSQL connection string
REDIS_URL              - Redis connection string
OPENAI_API_KEY         - OpenAI API key
ALLOWED_HOSTS          - Comma-separated list of allowed hosts
CORS_ALLOWED_ORIGINS   - Comma-separated CORS origins
```

## 🚢 Render Deployment

The `render.yaml` file defines:

- **Web Service**: Gunicorn serving Django app
- **Worker Service**: Celery worker for async tasks
- **PostgreSQL Database**: Persistent data storage
- **Redis Instance**: Cache + Celery broker

---

**Created**: May 28, 2026  
**Status**: Ready for Day 1 deployment

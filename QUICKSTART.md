# Quick Start - Day 1 Setup

## Prerequisites
- Python 3.9+
- PostgreSQL (local: `psql -U postgres`)
- Redis (local: `redis-server`)
- Git

## 1. Setup Local Environment

```bash
# Clone or enter project directory
cd AI-Customer-Support

# Create virtual environment
python -m venv venv

# Activate
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## 2. Configure Environment

```bash
# Copy template
cp .env.example .env

# Edit .env with your values:
# - SECRET_KEY: Generate with: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
# - DATABASE_URL: postgresql://postgres:password@localhost/customer_support
# - REDIS_URL: redis://localhost:6379/0
# - OPENAI_API_KEY: Your OpenAI API key
```

## 3. Database Setup

```bash
# Create PostgreSQL database
createdb -U postgres customer_support

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Verify setup
python manage.py check
```

## 4. Run Locally

```bash
# Terminal 1: Django dev server
python manage.py runserver

# Terminal 2: Celery worker
celery -A config worker --loglevel=info

# Terminal 3 (optional): Celery beat for scheduled tasks
celery -A config beat --loglevel=info
```

Access at: http://localhost:8000

Admin panel: http://localhost:8000/admin

## 5. Deploy to Render

```bash
# Initialize git repo
git init
git add .
git commit -m "Initial commit: Django scaffold with RAG"

# Push to GitHub
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/AI-Customer-Support.git
git push -u origin main

# Go to https://render.com
# 1. New → Web Service
# 2. Connect GitHub repository
# 3. Render detects render.yaml automatically
# 4. Deploy!

# After deployment:
# - Render Shell: python manage.py migrate
# - Create superuser on production
```

## File Structure Overview

```
AI-Customer-Support/
├── config/                      # Project configuration
│   ├── settings/
│   │   ├── base.py             # Shared settings
│   │   ├── local.py            # Dev settings
│   │   └── production.py        # Render settings
│   ├── wsgi.py, asgi.py
│   ├── urls.py
│   ├── celery.py
│   └── __init__.py
├── support/                     # Core support app
│   ├── models.py               # Document, Chunk, Conversation, Message, Ticket
│   ├── rag_utils.py            # Vector search, embeddings, RAG
│   ├── tasks.py                # Celery tasks
│   ├── views.py, urls.py
│   └── admin.py
├── accounts/                    # User management
│   ├── models.py               # UserProfile
│   ├── views.py, urls.py
│   └── admin.py
├── templates/                   # HTML templates
├── static/                      # CSS, JS, images
├── manage.py
├── requirements.txt            # All dependencies
├── render.yaml                 # Render deployment config
├── .env.example               # Environment template
├── .gitignore
└── README.md
```

## Key Commands

```bash
# Django
python manage.py runserver              # Start dev server
python manage.py migrate               # Apply migrations
python manage.py makemigrations        # Create migration
python manage.py createsuperuser       # Create admin user
python manage.py collectstatic         # Collect static files

# Celery
celery -A config worker --loglevel=info     # Start worker
celery -A config beat --loglevel=info       # Start scheduler
celery -A config purge                      # Clear task queue

# Utilities
python manage.py shell                 # Django Python shell
python manage.py check                 # Check configuration
```

## Environment Variables Checklist

- [ ] SECRET_KEY (generate fresh for production)
- [ ] DEBUG=False (production only)
- [ ] DATABASE_URL (PostgreSQL connection string)
- [ ] REDIS_URL (Redis connection string)
- [ ] OPENAI_API_KEY (for embeddings and responses)
- [ ] ALLOWED_HOSTS (comma-separated)
- [ ] CORS_ALLOWED_ORIGINS (comma-separated)

## Troubleshooting

**Import Error: pgvector**
```bash
# Make sure PostgreSQL has pgvector extension
# In Render: Extensions are auto-installed
# Local: CREATE EXTENSION IF NOT EXISTS vector;
```

**Celery connection refused**
```bash
# Ensure Redis is running
redis-server
# Windows: redis-server.exe (from WSL or standalone)
```

**Database URL format**
```
PostgreSQL: postgresql://user:password@host:port/database
SQLite (dev): sqlite:///db.sqlite3
```

---

**Status**: ✅ Ready for Day 1  
**Next**: Upload documents, build REST endpoints, test RAG pipeline

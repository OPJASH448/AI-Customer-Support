# 🤖 AI Customer Support Agent

<div align="center">

**A production-ready AI-powered customer support system with RAG vector search**

Built with Django 4.2 · Google Gemini · pgvector · Celery · Docker

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![Django](https://img.shields.io/badge/Django-4.2_LTS-092E20?style=flat&logo=django&logoColor=white)](https://djangoproject.com)
[![Gemini](https://img.shields.io/badge/Google_Gemini-2.0_Flash-4285F4?style=flat&logo=google&logoColor=white)](https://ai.google.dev)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16_+_pgvector-4169E1?style=flat&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=flat&logo=redis&logoColor=white)](https://redis.io)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

---

## 📑 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Quick Start](#-quick-start)
- [API Reference](#-api-reference)
- [Database Models](#-database-models)
- [RAG Pipeline](#-rag-pipeline)
- [Deployment](#-deployment)
- [Environment Variables](#-environment-variables)
- [Development Phases](#-development-phases)
- [Contributing](#-contributing)

---

## 🌟 Overview

AI Customer Support Agent is an intelligent customer support system that uses **Retrieval Augmented Generation (RAG)** to provide accurate, context-aware responses. Upload your knowledge base documents (PDF/TXT), and the AI agent uses **Google Gemini** to understand customer queries and respond with relevant information retrieved via **pgvector** semantic search.

---

## 🚀 Features

### Core AI Capabilities
- 🧠 **RAG-Powered Responses** — Semantic document search using pgvector + Gemini embeddings
- 📄 **Document Processing** — Upload PDF/TXT files, auto-chunk with token overlap, embed into 768-dim vectors
- 💬 **Multi-turn Conversations** — Track conversation history with context-aware AI responses
- 🎯 **Context Retrieval** — Top-K cosine similarity search (`<=>`) for the most relevant document chunks

### Platform Features
- 🔐 **JWT Authentication** — Secure token-based auth with 60-min access / 1-day refresh
- 🎫 **Priority Ticket Queue** — Fetch escalation tickets ordered by priority (`critical` > `high` > `medium` > `low`) with status filtering (GET `/api/tickets/`)
- 🛠️ **Ticket Resolution** — Resolves customer issues with agent replies and completion timestamps (PATCH `/api/tickets/{id}/resolve/`)
- 📊 **Real-time Analytics** — Deep analytics on total conversations, escalation rates, average resolution speed, and top unanswered topics (GET `/api/analytics/`)
- 📝 **Token Usage Logger** — Persistent JSONL token logging (`logs/token_usage.jsonl`) for prompt, completion, and total tokens with user tracking
- ⚡ **Async Task Processing** — Celery + Redis for background jobs (embedding, email escalation notifications, cleanup)
- 👤 **User Profiles** — Registration, authentication, and profile management
- 🛡️ **Production Security & Speed** — SSL, HSTS, CORS, per-user data isolation, and granular DB indexes on priority, status, and creation fields

### DevOps & Deployment
- 🐳 **Docker Compose** — One-command local dev environment (PostgreSQL + pgvector + Redis)
- 🚢 **Render-Ready** — Infrastructure as Code via `render.yaml` with automated migrations via `preDeployCommand`
- ⚙️ **3-Tier Settings** — Separate base, local, and production configurations with sqlite fallbacks
- 📦 **WhiteNoise** — Efficient compressed static file serving in production

---

## 🏗️ Architecture

```
                    ┌─────────────────────────────────────────────┐
                    │              Client (API Consumer)          │
                    └─────────────┬───────────────────────────────┘
                                  │ HTTPS + JWT
                    ┌─────────────▼───────────────────────────────┐
                    │         Django REST Framework API            │
                    │  ┌──────────┐  ┌──────────┐  ┌───────────┐ │
                    │  │ Accounts │  │ Support  │  │  Admin    │ │
                    │  │   API    │  │   API    │  │  Panel    │ │
                    │  └──────────┘  └────┬─────┘  └───────────┘ │
                    └─────────────────────┼───────────────────────┘
                                          │
                    ┌─────────────────────▼───────────────────────┐
                    │            RAG Pipeline Engine               │
                    │  ┌──────┐  ┌─────────┐  ┌───────────────┐  │
                    │  │Chunk │→ │ Embed   │→ │  Retrieve &   │  │
                    │  │Text  │  │(Gemini) │  │  Generate     │  │
                    │  └──────┘  └─────────┘  └───────────────┘  │
                    └──────┬──────────────────────────┬───────────┘
                           │                          │
              ┌────────────▼──────┐      ┌────────────▼──────┐
              │   PostgreSQL 16   │      │   Google Gemini   │
              │   + pgvector      │      │   2.0 Flash       │
              │   (768-dim vecs)  │      │   + Embedding API │
              └───────────────────┘      └───────────────────┘
                           │
              ┌────────────▼──────┐
              │   Redis 7         │
              │   (Celery Broker) │
              └───────────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| **Framework** | Django | 4.2 LTS | Web framework |
| **API** | Django REST Framework | 3.14 | RESTful endpoints |
| **Auth** | SimpleJWT | 5.2 | JWT authentication |
| **AI / LLM** | Google Gemini | 2.0 Flash | Response generation |
| **Embeddings** | Gemini Embedding | 001 | 768-dim vector embeddings |
| **Vector DB** | pgvector | 0.4.2 | PostgreSQL vector similarity search + HNSW index |
| **Database** | PostgreSQL | 16 | Primary data store |
| **Cache/Broker** | Redis | 7 | Celery task broker |
| **Async Tasks** | Celery | 5.3 | Background job processing |
| **WSGI** | Gunicorn | 20.1 | Production server |
| **Static Files** | WhiteNoise | 6.4 | Compressed static file serving |
| **PDF Parsing** | PyPDF2 | 3.0+ | Document text extraction |
| **Tokenization** | tiktoken | 0.5+ | Token counting & chunking |
| **Config** | django-environ | — | Environment variable management |
| **Deployment** | Render | — | Cloud PaaS hosting |
| **Containers** | Docker Compose | 3.9 | Local development |

---

## 📁 Project Structure

```
AI-Customer-Support/
│
├── config/                          # Django project configuration
│   ├── __init__.py                  # Celery app export
│   ├── celery.py                    # Celery configuration
│   ├── urls.py                      # Root URL routing + health check
│   ├── wsgi.py                      # WSGI application
│   ├── asgi.py                      # ASGI application
│   └── settings/
│       ├── __init__.py              # Auto-selects local/production
│       ├── base.py                  # Shared settings (apps, JWT, CORS, Gemini)
│       ├── local.py                 # Development (Debug=True, Docker DB)
│       └── production.py            # Production (SSL, HSTS, Render)
│
├── support/                         # Core RAG support app
│   ├── models.py                    # Document, DocumentChunk (+HNSW index), Conversation, Message, EscalationTicket
│   ├── views.py                     # 4 ViewSets + RAGAskView + TicketListView + AnalyticsView
│   ├── chat_view.py                 # Optimized RAG Chat APIView with query chunking + RRF fusion
│   ├── rag.py                       # embed_query, retrieve_similar_chunks, generate_grounded_answer
│   ├── rag_utils.py                 # Query chunking, batch embedding, fused RRF vector search
│   ├── token_logger.py              # Persistent Gemini token usage logger (JSONL)
│   ├── serializers.py               # 6 DRF serializers with validation
│   ├── urls.py                      # DRF router + RAG ask endpoint
│   ├── tasks.py                     # 4 Celery tasks (process_document, escalate, cleanup, test)
│   ├── admin.py                     # Django admin registration
│   └── migrations/                  # Database migrations
│       └── 0005_documentchunk_docchunk_embed_hnsw_idx.py  # HNSW index migration
│
├── accounts/                        # User management app
│   ├── models.py                    # UserProfile model
│   ├── views.py                     # Register, Profile, JWT views
│   ├── serializers.py               # 4 serializers (User, Profile, Register, JWT)
│   ├── urls.py                      # Auth + profile endpoints
│   ├── admin.py                     # Admin registration
│   └── migrations/                  # Database migrations
│
├── templates/                       # Django templates (future frontend)
├── static/                          # Static assets (future CSS/JS)
├── media/                           # Uploaded documents storage
├── staticfiles/                     # Collected static files (WhiteNoise)
│
├── docker-compose.yml               # Local dev: PostgreSQL + Redis
├── render.yaml                      # Render deployment IaC
├── requirements.txt                 # Python dependencies (pgvector upgraded to 0.4.2)
├── manage.py                        # Django management
├── .env.example                     # Environment template
├── .gitignore                       # Git exclusions
│
├── test_pdf_flow.py                 # End-to-end PDF upload → chunk → embed pipeline test
├── test_rag_ask.py                  # RAG Ask endpoint full pipeline test
├── test_remaining.py                # HNSW retrieval, LLM generation, citation, history test
│
├── README.md                        # ← You are here
├── README_PHASE2.md                 # Phase 2 detailed changelog
├── CHECKLIST.md                     # Development checklist
├── QUICKSTART.md                    # Quick start guide
├── RENDER_DEPLOYMENT.md             # Render deployment guide
├── DATABASE_VERIFICATION.md         # DB setup verification
├── DEPLOY_NOW.md                    # Deployment instructions
├── DAY1_COMPLETION.md               # Phase 1 completion report
├── DAY1_FINAL_TEST.md               # Phase 1 test results
├── DAY1_FINAL_VERDICT.md            # Phase 1 final verdict
├── DAY1_RESOLUTION.md               # Phase 1 issue resolutions
└── TEST_RESULTS.md                  # Test results summary
```

---

## ⚡ Quick Start

### Prerequisites
- Python 3.10+
- Docker & Docker Compose
- Git
- A [Google Gemini API key](https://ai.google.dev/)

### 1. Clone & Setup

```bash
# Clone the repository
git clone https://github.com/OPJASH448/AI-Customer-Support.git
cd AI-Customer-Support

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Start Infrastructure

```bash
# Start PostgreSQL (pgvector) + Redis via Docker
docker-compose up -d

# Verify services are running
docker-compose ps
```

### 3. Configure Environment

```bash
# Copy environment template
cp .env.example .env
```

Edit `.env` with your settings:
```env
SECRET_KEY=your-generated-secret-key
DEBUG=True
DJANGO_SETTINGS_MODULE=config.settings.local

# Docker services
DATABASE_URL=postgresql://postgres:password@localhost:5433/ai_support
REDIS_URL=redis://localhost:6380/0

# Google Gemini (required for RAG)
GEMINI_API_KEY=your-gemini-api-key-here

ALLOWED_HOSTS=localhost,127.0.0.1
```

### 4. Initialize Database

```bash
# Run migrations
python manage.py migrate

# Create admin user
python manage.py createsuperuser
```

### 5. Run the Server

```bash
# Start Django development server
python manage.py runserver

# (Optional) In a separate terminal, start Celery worker
celery -A config worker --loglevel=info
```

### 6. Test the API

```bash
# Health check
curl http://localhost:8000/

# Register a user
curl -X POST http://localhost:8000/api/accounts/register/register/ \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "email": "test@example.com", "password": "SecurePass123!", "password2": "SecurePass123!"}'

# Login (get JWT token)
curl -X POST http://localhost:8000/api/accounts/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "SecurePass123!"}'

# Upload a document (use the access token from login)
curl -X POST http://localhost:8000/api/support/documents/ \
  -H "Authorization: Bearer <your-access-token>" \
  -F "title=My Knowledge Base" \
  -F "file=@document.pdf" \
  -F "source=internal"
```

---

## 📡 API Reference

### Authentication Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `POST` | `/api/accounts/register/register/` | Register new user | Public |
| `POST` | `/api/accounts/token/` | Login → JWT access + refresh tokens | Public |
| `POST` | `/api/accounts/token/refresh/` | Refresh expired access token | Public |
| `GET` | `/api/accounts/profiles/me/` | Get current user's profile | JWT |
| `PUT/PATCH` | `/api/accounts/profiles/update_profile/` | Update user profile | JWT |

### Document Management

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/api/support/documents/` | List user's documents | JWT |
| `POST` | `/api/support/documents/` | Upload document (multipart: PDF/TXT) | JWT |
| `GET` | `/api/support/documents/{id}/` | Get document details + chunks | JWT |
| `GET` | `/api/support/documents/{id}/chunks/` | Get document's vector chunks | JWT |
| `GET` | `/api/support/documents/{id}/status/` | Check processing status | JWT |
| `DELETE` | `/api/support/documents/{id}/` | Delete document | JWT |

### RAG Chat Endpoint

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `POST` | `/api/chat/` | RAG multi-turn query: vector search → Gemini 2.0 Flash response → context citation → auto-escalation | JWT |

### Conversations & Messages

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/api/support/conversations/` | List user's conversations | JWT |
| `POST` | `/api/support/conversations/` | Create new conversation | JWT |
| `GET` | `/api/support/conversations/{id}/messages/` | Get conversation messages | JWT |
| `GET` | `/api/support/messages/` | List user's messages | JWT |
| `POST` | `/api/support/messages/` | Send a message | JWT |

### Ticket Queue & Analytics

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/api/tickets/` | Priority Queue API — Returns active tickets ordered by priority (`critical` > `high` > `medium` > `low`), supports status filtering | JWT |
| `PATCH` | `/api/tickets/{id}/resolve/` | Resolve Ticket API — Updates status to `resolved`, saves `agent_reply` and `resolved_at` timestamp | JWT |
| `GET` | `/api/analytics/` | Live Analytics Dashboard API — Aggregates key CS metrics: conversations, escalation rate, resolution times, and top unanswered topics | JWT |

### Escalation Tickets (Standard CRUD)

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/api/support/escalations/` | List all escalation tickets | JWT |
| `POST` | `/api/support/escalations/` | Create escalation ticket | JWT |
| `GET` | `/api/support/escalations/{id}/` | Get ticket details | JWT |
| `PUT/PATCH` | `/api/support/escalations/{id}/` | Update ticket (status, assignee) | JWT |

### System

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/` | Health check + API directory | Public |
| `GET` | `/admin/` | Django admin panel | Staff |

---

## 🗄️ Database Models

### `Document`
Knowledge base documents uploaded by users.

| Field | Type | Description |
|-------|------|-------------|
| `title` | CharField(255) | Document title |
| `content` | TextField (nullable) | Extracted text content |
| `file` | FileField | Uploaded file (PDF/TXT) |
| `source` | CharField(255) | Document source identifier |
| `status` | CharField | `processing` → `ready` / `failed` |
| `uploaded_by` | FK → User | Document owner |
| `is_active` | Boolean | Soft delete flag |

### `DocumentChunk`
Vector-embedded chunks for RAG retrieval.

| Field | Type | Description |
|-------|------|-------------|
| `document` | FK → Document | Parent document |
| `content` | TextField | Chunk text content |
| `chunk_index` | Integer | Position in document |
| `embedding` | VectorField(768) | Gemini embedding vector |
| `tokens` | Integer | Token count |

### `Conversation`
Multi-turn conversation sessions.

| Field | Type | Description |
|-------|------|-------------|
| `user` | FK → User | Conversation owner |
| `title` | CharField | Conversation title |
| `is_active` | Boolean | Active status |

### `Message`
Individual messages within conversations.

| Field | Type | Description |
|-------|------|-------------|
| `conversation` | FK → Conversation | Parent conversation |
| `role` | CharField | `user` or `assistant` |
| `content` | TextField | Message text |
| `tokens_used` | Integer | Token usage |
| `context_chunks` | M2M → DocumentChunk | RAG context used |

### `EscalationTicket`
Issues requiring human review.

| Field | Type | Description |
|-------|------|-------------|
| `conversation` | FK → Conversation | Related conversation |
| `issue` | TextField | Issue description |
| `priority` | CharField | `low` / `medium` / `high` / `critical` (mapped from priority scores) |
| `status` | CharField | `open` / `in_progress` / `resolved` / `closed` |
| `assigned_to` | FK → User | Assigned agent |
| `agent_reply` | TextField (nullable) | Support agent's reply to the customer |
| `resolved_at` | DateTimeField (nullable) | Timestamp of when the ticket was resolved |

### `UserProfile`
Extended user profile.

| Field | Type | Description |
|-------|------|-------------|
| `user` | OneToOne → User | Django User link |
| `bio` | TextField | User biography |
| `avatar` | ImageField | Profile picture |

---

## 🧠 RAG Pipeline

The Retrieval Augmented Generation pipeline is the core intelligence of this system:

### How It Works

```
1. INGEST                    2. QUERY                     3. RESPOND
─────────────               ─────────────                ─────────────
┌─────────┐                 ┌─────────┐                  ┌──────────┐
│  Upload  │                │  User   │                  │  Gemini  │
│  PDF/TXT │                │  Query  │                  │  2.0     │
└────┬─────┘                └────┬────┘                  │  Flash   │
     │                           │                       └────┬─────┘
     ▼                           ▼                            │
┌─────────┐                 ┌─────────┐                       │
│  Extract │                │  Embed  │                       ▼
│  Text    │                │  Query  │               ┌──────────────┐
└────┬─────┘                └────┬────┘               │   Generate   │
     │                           │                    │   Response   │
     ▼                           ▼                    │  with context│
┌─────────┐                 ┌──────────┐              └──────────────┘
│  Chunk  │                 │  Vector  │                      ▲
│  500tok │                 │  Search  │──────────────────────┘
│  50 ovl │                 │  Top-5   │        Retrieved chunks
└────┬────┘                 │  <->     │        as context
     │                      └──────────┘
     ▼
┌──────────┐
│  Embed   │
│  Gemini  │
│  768-dim │
└────┬─────┘
     │
     ▼
┌──────────┐
│ pgvector │
│  Store   │
└──────────┘
```

### Configuration

| Parameter | Value | Description |
|-----------|-------|-------------|
| Embedding Model | `gemini-embedding-001` | Google Gemini embeddings |
| Embedding Dimensions | 768 | Vector size |
| Generation Model | `gemini-2.0-flash` | Response generation |
| Chunk Size | 500 tokens | Window size for splitting |
| Chunk Overlap | 50 tokens | Sliding window overlap |
| Top-K Retrieval | 5 | Number of chunks retrieved |
| Max Output Tokens | 600–1000 | Response length limit |
| Temperature | 0.3 | Response creativity (low = factual) |
| Vector Index | HNSW (`vector_cosine_ops`) | pgvector ANN index — O(log N) search |
| Query Chunking | Auto (>400 chars) | Long queries split to prevent embedding dilution |
| Fusion Strategy | Reciprocal Rank Fusion (RRF) | Multi-chunk results merged by 1/rank scoring |

---

## 🚢 Deployment

### Deploy to Render

The project includes a `render.yaml` for one-click deployment:

```bash
# 1. Push to GitHub
git add .
git commit -m "Deploy to Render"
git push origin master

# 2. Go to https://render.com
# 3. Connect your GitHub repository
# 4. Render auto-detects render.yaml and deploys:
#    - Web Service (Gunicorn)
#    - Worker Service (Celery)
#    - PostgreSQL Database
#    - Redis Instance

# 5. After deployment, run in Render Shell:
python manage.py migrate
python manage.py createsuperuser
```

### Render Services (via `render.yaml`)

| Service | Type | Description |
|---------|------|-------------|
| `support-agent-web` | Web Service | Django + Gunicorn |
| `support-agent-worker` | Worker | Celery background tasks |
| `support-db` | PostgreSQL | Managed database |
| `support-redis` | Redis | Managed cache/broker |

### Docker (Local Development)

```bash
# Start services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Reset data
docker-compose down -v
```

---

## 🔐 Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | ✅ | dev-key | Django secret key |
| `DEBUG` | ❌ | `False` | Debug mode |
| `DJANGO_SETTINGS_MODULE` | ❌ | auto-detected | Settings module |
| `DATABASE_URL` | ✅ | sqlite | PostgreSQL connection string |
| `REDIS_URL` | ✅ | `localhost:6380` | Redis connection string |
| `GEMINI_API_KEY` | ✅ | — | Google Gemini API key |
| `ALLOWED_HOSTS` | ❌ | localhost | Comma-separated allowed hosts |
| `CORS_ALLOWED_ORIGINS` | ❌ | localhost | Comma-separated CORS origins |
| `RENDER` | ❌ | `false` | Set to `true` on Render |
| `EMAIL_HOST` | ❌ | `smtp.gmail.com` | SMTP host for notifications |
| `EMAIL_PORT` | ❌ | `587` | SMTP port |
| `EMAIL_HOST_USER` | ❌ | — | SMTP username |
| `EMAIL_HOST_PASSWORD` | ❌ | — | SMTP password |

See [.env.example](.env.example) for the full template.

---

## 📅 Development Phases

### ✅ Phase 1 — Foundation (Completed)
- Django 4.2 project scaffold with 3-tier settings
- 2 Django apps: `support` (5 models) + `accounts` (1 model)
- Database migrations and Django admin
- Celery + Redis configuration
- JWT authentication setup
- Render deployment configuration
- Clean Git repository + comprehensive documentation

### ✅ Phase 2 — RAG Pipeline, Ticket Queue & Analytics (Completed)
- **Google Gemini Integration** — Semantic embeddings (`gemini-embedding-001`) + generation (`gemini-2.0-flash`)
- **Full RAG Pipeline** — Upload PDF/TXT, auto-chunk with tiktoken token counting, 768-dim vector storage in pgvector, and cosine distance search (`<=>`)
- **RAG Chat API** (`POST /api/chat/`) — Generates Gemini answers citing sources, logs prompt/completion tokens to `token_usage.jsonl`, scores query urgency, and auto-escalates low-confidence answers
- **Ticket Queue API** (`GET /api/tickets/`) — High-performance priority queue sorting tickets (`critical` > `high` > `medium` > `low`) with status filters
- **Ticket Resolution API** (`PATCH /api/tickets/{id}/resolve/`) — Allows agents to resolve tickets with a reply and records completion timestamps
- **Analytics Dashboard API** (`GET /api/analytics/`) — Generates deep real-time metrics including average resolution time and top unanswered topics
- **Database Optimizations** — Granular indexes on priority, status, and conversation timestamps for high scalability
- **Production-Ready Deployment** — Automated migrations via Render's `preDeployCommand`, UTF-8 requirements, and resilient production settings

> 📄 See [README_PHASE2.md](README_PHASE2.md) for the detailed Phase 2 changelog.

### ✅ Phase 3 — RAG Optimization & Vector Search Hardening (Completed)

#### pgvector HNSW Index
- Upgraded `pgvector` to `0.4.2` to unlock `HnswIndex` support
- Added `HnswIndex(fields=['embedding'], opclasses=['vector_cosine_ops'])` on `DocumentChunk` model
- Generated and applied Django migration `0005_documentchunk_docchunk_embed_hnsw_idx.py`
- Reduces vector search complexity from **O(N)** linear scan to **O(log N)** Approximate Nearest Neighbour search

#### Smart Query Chunking
- Long user queries (>400 chars) are automatically split into semantic sentence-level chunks
- Prevents **embedding dilution** — single vectors for multi-topic queries lose semantic precision
- Short queries bypass chunking for sub-second response latency

#### Reciprocal Rank Fusion (RRF)
- Each query chunk independently searches the pgvector HNSW index
- Results merged using RRF: `score(chunk) = Σ 1/rank` across all query embeddings
- Guarantees top-5 most contextually relevant chunks even for cross-topic or compound questions

#### Batch Embedding
- Multiple query chunks sent to Gemini embedding API in a single batch call
- Falls back to sequential calls if batch API is unavailable

#### Bug Fixes
- Fixed missing `PdfReader` import in `support/tasks.py`
- Fixed `gemini-1.5-flash` → `gemini-2.0-flash` model name in `support/rag.py`
- Added proper HTTP 429 handling in `RAGAskView` for Gemini rate limits
- Fixed `document.documentchunk_set` → `document.chunks` reverse relation throughout codebase

### 🔜 Phase 4 — Frontend & Polish (Upcoming)
- [ ] Interactive Chat & Admin Dashboard Frontend (Tailwind + React/HTML5)
- [ ] Swagger/OpenAPI documentation schema
- [ ] WebSocket real-time chat & notifications
- [ ] Detailed Rate Limiting & User quotas

---

## 🧪 End-to-End Pipeline Test Results

Full pipeline tested with a real PDF (`JaswanthKanipakam.23BCS123.pdf`) on 2026-06-03.

| Component | Status | Details |
|---|---|---|
| PDF Upload API | ✅ Pass | `POST /api/support/documents/` → HTTP 201 |
| PDF Parsing (PyPDF2) | ✅ Pass | Text extracted from all pages |
| Chunk Creation | ✅ Pass | 3 chunks created (500-tok, 50-tok overlap) |
| Embedding Generation | ✅ Pass | 768-dim vectors via `gemini-embedding-001` |
| pgvector Storage | ✅ Pass | Chunks stored + retrievable from PostgreSQL |
| HNSW Vector Index Retrieval | ✅ Pass | Top-5 chunks ranked by cosine distance |
| LLM Answer Generation | ✅ Pass | Grounded answer via `gemini-2.0-flash` |
| Source Citation Return | ✅ Pass | 5 cited sources with `document_title` + `distance` |
| Conversation History Saving | ✅ Pass | Messages persisted, context_chunks linked, DB assertions passed |

### Sample HNSW Retrieval Result

```
Query: "what are the achievements of jaswanth"
[1] Jaswanth Kanipakam CV  | Chunk#0 | Cosine Distance: 0.26260  <- Best match
[2] Jaswanth Kanipakam CV  | Chunk#1 | Cosine Distance: 0.40879
[3] Jaswanth Kanipakam CV  | Chunk#2 | Cosine Distance: 0.45843
[4] opp.txt Robot Code     | Chunk#0 | Cosine Distance: 0.53509
[5] Test Processing        | Chunk#0 | Cosine Distance: 0.53509
```

> All 3 CV chunks ranked highest — HNSW cosine search correctly identifies the most relevant document.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit changes: `git commit -m "Add my feature"`
4. Push to branch: `git push origin feature/my-feature`
5. Open a Pull Request

---

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

---

<div align="center">

**Created**: May 28, 2026 | **Phase 2 Completed**: May 2026 | **Phase 3 Completed**: June 2026  
**Author**: [OPJASH448](https://github.com/OPJASH448)

⭐ Star this repo if you find it helpful!

</div>

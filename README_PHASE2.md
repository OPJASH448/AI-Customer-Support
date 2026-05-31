# 📘 Phase 2 — RAG Pipeline & AI Integration

> **AI Customer Support Agent** — Phase 2 Development Summary  
> Completed: May 2026 | Built with Django 4.2 + Google Gemini + pgvector

---

## 🎯 Phase 2 Objectives

Phase 2 focused on transforming the Phase 1 scaffold into a **functional AI-powered customer support system** with a complete RAG (Retrieval Augmented Generation) pipeline, Google Gemini LLM integration, Docker-based development environment, and production-ready API endpoints.

---

## 🆕 What Changed in Phase 2

### 🔄 LLM Migration: OpenAI → Google Gemini
The AI backbone was migrated from OpenAI to **Google Gemini**, providing:

| Feature | Phase 1 (Planned) | Phase 2 (Implemented) |
|---------|-------------------|----------------------|
| **Embedding Model** | `text-embedding-3-small` (1536 dims) | `gemini-embedding-001` (768 dims) |
| **Generation Model** | GPT-3.5 / GPT-4 | `gemini-2.0-flash` |
| **API Key** | `OPENAI_API_KEY` | `GEMINI_API_KEY` |
| **Vector Dimensions** | 1536 | 768 |

### 🧠 RAG Pipeline Implementation

The complete RAG pipeline is now operational:

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Document   │────▶│   Chunking   │────▶│  Embedding   │────▶│   pgvector   │
│   Upload     │     │  (tiktoken)  │     │  (Gemini)    │     │   Storage    │
│  PDF / TXT   │     │ 500tok/50ovl │     │  768 dims    │     │              │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                                                                       │
┌──────────────┐     ┌──────────────┐     ┌──────────────┐            │
│   Response   │◀────│   Gemini     │◀────│   Context    │◀───────────┘
│   Delivery   │     │  2.0 Flash   │     │  Retrieval   │
│              │     │              │     │  Top-5 <->   │
└──────────────┘     └──────────────┘     └──────────────┘
```

#### Document Processing Pipeline (`support/tasks.py`)
1. **Text Extraction** — PDF (via PyPDF2) and TXT file support
2. **Token-Based Chunking** — 500-token windows with 50-token overlap using `tiktoken`
3. **Embedding Generation** — Google Gemini `gemini-embedding-001` (768-dimensional vectors)
4. **Bulk Storage** — Efficient `bulk_create()` for `DocumentChunk` objects with pgvector embeddings
5. **Status Tracking** — Document status lifecycle: `processing` → `ready` / `failed`

#### Context Retrieval & Response Generation (`support/rag_utils.py`)
- **`embed_text()`** — Generates 768-dim embeddings via Gemini API
- **`retrieve_context()`** — Raw SQL pgvector similarity search using `<->` cosine distance operator
- **`generate_response()`** — Full RAG pipeline: retrieve top-5 chunks → build system+context prompt → call `gemini-2.0-flash` → save response with context chunks
- **`split_document_into_chunks()`** — Character-based splitting utility (500 chars, 100 overlap)

---

### 🐳 Docker Development Environment

A new `docker-compose.yml` provides a local development stack:

```yaml
Services:
  db:   pgvector/pgvector:pg16  →  localhost:5433
  redis: redis:7-alpine         →  localhost:6380
```

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| **PostgreSQL** | `pgvector/pgvector:pg16` | `5433:5432` | Vector-enabled database |
| **Redis** | `redis:7-alpine` | `6380:6379` | Celery broker & cache |

Both services include:
- ✅ Persistent volumes (`postgres_data`, `redis_data`)
- ✅ Health checks with retries
- ✅ Automatic restart policy

**Quick Start:**
```bash
docker-compose up -d
# PostgreSQL with pgvector: localhost:5433
# Redis: localhost:6380
```

---

### 📡 API Endpoints (Fully Implemented)

#### Support API (`/api/support/`)
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/api/support/documents/` | List user's documents | JWT |
| `POST` | `/api/support/documents/` | Upload document (PDF/TXT, multipart) | JWT |
| `GET` | `/api/support/documents/{id}/` | Get document detail | JWT |
| `GET` | `/api/support/documents/{id}/chunks/` | Get document chunks | JWT |
| `GET` | `/api/support/documents/{id}/status/` | Check processing status | JWT |
| `GET` | `/api/support/conversations/` | List conversations | JWT |
| `POST` | `/api/support/conversations/` | Create new conversation | JWT |
| `GET` | `/api/support/conversations/{id}/messages/` | Get conversation messages | JWT |
| `GET/POST` | `/api/support/messages/` | List/create messages | JWT |
| `GET/POST` | `/api/support/escalations/` | List/create escalation tickets | JWT |

#### RAG Chat API (`/api/chat/`)
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `POST` | `/api/chat/` | RAG query endpoint: vector search → prompt build → Gemini generation → citation → auto-escalation | JWT |

#### Accounts API (`/api/accounts/`)
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `POST` | `/api/accounts/register/register/` | User registration | Public |
| `POST` | `/api/accounts/token/` | JWT login (access + refresh) | Public |
| `POST` | `/api/accounts/token/refresh/` | Refresh JWT token | Public |
| `GET` | `/api/accounts/profiles/me/` | Get current user profile | JWT |
| `PUT/PATCH` | `/api/accounts/profiles/update_profile/` | Update profile | JWT |

#### Root (`/`)
| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/` | Health check + API documentation | Public |
| `GET` | `/admin/` | Django admin interface | Staff |

---

### 🗄️ Database Schema Updates

#### New Migration: `0002_document_file_document_status_alter_document_content`
- Added `file` field (FileField) to Document model for actual file uploads
- Added `status` field with choices: `processing`, `ready`, `failed`
- Made `content` field nullable (text extracted from file during processing)

#### New Migration: `0003_alter_documentchunk_embedding`
- Changed embedding dimensions from 1536 → **768** (Gemini embedding dimension)

---

### 🔧 Configuration Updates

#### `config/settings/base.py`
```python
# New Gemini configuration
GEMINI_API_KEY = env('GEMINI_API_KEY', default='')
PGVECTOR_DIMENSION = 768  # Google Gemini embedding dimension

# Updated Celery to use port 6380 (Docker)
CELERY_BROKER_URL = env('REDIS_URL', default='redis://localhost:6380/0')
```

#### `config/settings/local.py`
- PostgreSQL connection via Docker on port `5433`
- Database name: `ai_support`
- Debug mode with console email backend

#### `config/__init__.py`
- Added Celery app export for proper task autodiscovery

---

### 📦 New Files Created

| File | Purpose |
|------|---------|
| `support/chat_view.py` | RAG Chat APIView (`POST /api/chat/`) with pgvector search & auto-escalation |
| `support/token_logger.py` | Persistent token logger recording stats to `logs/token_usage.jsonl` |
| `support/serializers.py` | 6 DRF serializers (Document, Upload, Chunk, Conversation, Message, Escalation) |
| `accounts/serializers.py` | 4 DRF serializers (User, Profile, Register, JWT) |
| `support/migrations/0002_*.py` | File upload & status migration |
| `support/migrations/0003_*.py` | Embedding dimension migration (768) |
| `docker-compose.yml` | Local PostgreSQL + Redis stack |

### 📝 Files Modified

| File | Key Changes |
|------|-------------|
| `support/views.py` | Full ViewSet implementations with document upload, sync processing |
| `support/tasks.py` | Gemini embedding, PDF extraction, token-based chunking |
| `support/rag_utils.py` | Complete RAG pipeline (embed → retrieve → generate) |
| `support/models.py` | File field, status field, 768-dim vectors |
| `support/urls.py` | DRF router with 4 registered viewsets |
| `config/urls.py` | API root health check, support & accounts includes, added `ChatView` path |
| `config/settings/base.py` | Gemini config, pgvector dimension, updated Celery |
| `config/settings/local.py` | Docker-based database configuration |
| `accounts/views.py` | Registration, profile, and JWT views |
| `accounts/urls.py` | Router + JWT token endpoints |
| `requirements.txt` | Updated dependencies (google-generativeai, etc.) |
| `.gitignore` | Added persistent `logs/` directory |

### 🗑️ Files Removed
| File | Reason |
|------|--------|
| `POSTGRESQL_READY.md` | Superseded by Docker setup |
| `YOUR_QUESTION_ANSWERED.md` | One-time documentation, no longer needed |

---

## 🧪 Celery Tasks

| Task | Type | Description |
|------|------|-------------|
| `test_celery_task` | On-demand | Connectivity test for Celery + Redis |
| `process_document` | On-demand | Full document → chunks → embeddings pipeline |
| `escalate_conversation` | On-demand | Create escalation ticket + email notification |
| `cleanup_old_conversations` | Scheduled (Beat) | Archive conversations older than 30 days |

> **Note:** Document processing currently runs **synchronously** in the HTTP request cycle to ensure reliability without a running Celery worker. Celery `.delay()` can be enabled when workers are available.

---

## 🔐 Security Features

- ✅ JWT Authentication (60-min access, 1-day refresh tokens)
- ✅ Per-user data isolation (users only see their own documents/conversations)
- ✅ CORS configuration with allowed origins
- ✅ WhiteNoise for secure static file serving
- ✅ Production SSL redirect and HSTS headers
- ✅ Environment-based secret management
- ✅ File upload validation (PDF/TXT only, 50MB limit)

---

## 📊 Phase 2 Completion Status

| Category | Status | Details |
|----------|--------|---------|
| Gemini Integration | ✅ Complete | Embeddings + generation working |
| RAG Pipeline | ✅ Complete | Document → chunks → embed → retrieve → respond |
| Document Upload API | ✅ Complete | PDF/TXT with multipart upload |
| RAG Chat API Endpoint | ✅ Complete | POST `/api/chat/` with cosine search & auto-escalation |
| REST API Endpoints | ✅ Complete | 11+ endpoints across 2 apps |
| Token Usage Logger | ✅ Complete | Logged to persistent JSONL file |
| JWT Authentication | ✅ Complete | Register, login, refresh, profile |
| Docker Dev Environment | ✅ Complete | PostgreSQL + pgvector + Redis |
| Database Migrations | ✅ Complete | File field, status, 768-dim embeddings |
| Serializers | ✅ Complete | 10 serializers across 2 apps |
| Celery Tasks | ✅ Complete | 4 tasks with error handling |
| Production Config | ✅ Complete | Render.yaml + production settings |

---

## 🚀 What's Next (Phase 3)

- [ ] Frontend chat interface (HTMX + Tailwind or React)
- [x] Expose RAG response as a dedicated chat endpoint (`/api/chat/`)
- [ ] Swagger/OpenAPI documentation
- [ ] Unit & integration test coverage
- [ ] Rate limiting for API endpoints
- [x] Token usage analytics logger & aggregator
- [ ] Celery async processing with `.delay()`
- [ ] WebSocket support for real-time chat

---

**Phase 2 Completed**: May 2026  
**Author**: OPJASH448  
**Repository**: [github.com/OPJASH448/AI-Customer-Support](https://github.com/OPJASH448/AI-Customer-Support)

# Professional Resume Impact Points

These bullet points are ready to copy directly into the projects section of your resume. They use action verbs, quantify accomplishments, and highlight your architectural choices (Google Gemini, Supabase, Upstash, pgvector, Celery).

---

## 🛠️ Core Technology Highlights (Keywords to Include in Skills Section)
- **Backend**: Python, Django, Django REST Framework (DRF)
- **AI/LLM**: Google Gemini 2.0 Flash, Gemini Embedding (`gemini-embedding-001`)
- **Database/Vector Search**: PostgreSQL, pgvector, HNSW Indexing, BM25 Search
- **Caching & Broker**: Upstash Redis (Secure TLS/SSL, `rediss://`)
- **Async Task Queue**: Celery (Background Document Processing, Email Alerts)
- **Cloud/Storage**: Supabase Storage, Supabase PostgreSQL, Render PaaS, Docker Compose

---

## 🚀 Impact Bullet Points for your Resume

### Option 1: Full-Stack / AI-focused Role (Highly Detailed)
* **Architected and deployed a Production-Grade AI Customer Support Agent** using **Django REST Framework** and **Google Gemini 2.0**, serving grounded answers to customer queries with sub-second retrieval latency.
* **Designed a Hybrid RAG (Retrieval-Augmented Generation) Pipeline** combining semantic vector search (**pgvector HNSW index**) and keyword retrieval (**BM25**), merged via **Reciprocal Rank Fusion (RRF)** to increase search precision and eliminate keyword/semantic blind spots.
* **Engineered an Asynchronous Document Processing Pipeline** using **Celery** and **Upstash Redis** (TLS secured), enabling users to upload PDF/TXT manuals, auto-chunk texts via **tiktoken**, and generate/save embeddings out-of-band to prevent thread-blocking on the web server.
* **Eliminated local file dependencies** by migrating media storage to **Supabase Storage** and routing requests through the **Supabase Connection Pooler** on port 5432, enabling robust IPv4/IPv6 compatibility and secure multi-tenant access.
* **Hardened application security** by configuring SSL/TLS bindings, enforcing **Row Level Security (RLS)** on internal PostgreSQL metadata tables, and developing token rate-limit policies to defend Gemini LLM endpoints against API abuse.

### Option 2: Backend / DevOps-focused Role (Shorter & Punchy)
* **Developed an asynchronous AI search platform** utilizing **Django**, **Celery**, and **Upstash Redis**, reducing API response times by delegating compute-heavy document vectorizations to background workers.
* **Configured an advanced pgvector search engine** using **HNSW indices** to enable $O(\log N)$ vector search on 768-dimensional Google Gemini embeddings, replacing linear search scans and optimizing query performance.
* **Established a cloud-native storage infrastructure** using **Supabase Storage** and private/signed URLs to enable persistent, decoupled document management, reducing server disk usage to zero.
* **Constructed Infrastructure-as-Code (IaC) deployment pipelines** via **Render**, orchestrating automated migrations, static file compression (WhiteNoise), and secure environment syncs for web and worker services.

---

## 🧠 Key Interview Discussion Points (To wow interviewers)
1. **RRF & Hybrid Search**: Explain how Dense embeddings fail on exact matches like "Error Code 4021" and Sparse BM25 fails on semantic concepts like "how to log in". By combining both and ranking them using Reciprocal Rank Fusion ($1/(k + \text{rank})$), you achieved state-of-the-art information retrieval.
2. **Asynchronous Vector Ingestion**: Discuss how parsing and embedding a 140KB PDF involves multiple slow HTTP requests. By using Celery, the user gets an instant `201 Created` while background workers securely parse, chunk, embed, and store vectors out-of-band.
3. **Database Security & IPv6 Compatibility**: Explain how Supabase is IPv6-only by default and caused timeouts on IPv4-only networks. Explain that you resolved this by routing connections through Supabase's **Session Pooler** (which has dual-stack DNS) and securing database metadata tables using **Row Level Security (RLS)**.

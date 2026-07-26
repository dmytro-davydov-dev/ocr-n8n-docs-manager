# Contract Review [MVP](docs/Tech-Glossary.md#mvp)

An [AI](docs/Tech-Glossary.md#ai)-assisted contract review application demonstrating a modern document-processing architecture using **[React](docs/Tech-Glossary.md#react)**, **[FastAPI](docs/Tech-Glossary.md#fastapi)**, **[Celery](docs/Tech-Glossary.md#celery)**, **[n8n](docs/Tech-Glossary.md#n8n)**, **[PostgreSQL](docs/Tech-Glossary.md#postgresql)**, **[Redis](docs/Tech-Glossary.md#redis)**, [OCR](docs/Tech-Glossary.md#ocr), and [LLMs](docs/Tech-Glossary.md#llm).

The repository is both:

- a production-minded reference implementation; and
- an Obsidian Architecture Knowledge Base documenting decisions, requirements, and implementation.

## Architecture

```text
React
   ↓
FastAPI
   ↓
n8n (workflow orchestration)
   ↓
Celery Worker
   ↓
PDF → OCR → Chunking → LLM → Summary
   ↓
PostgreSQL + Local Storage
```

## Architecture at a glance

React ([Vite](docs/Tech-Glossary.md#vite)/TS) talks to FastAPI, which is the only service allowed to write application data. FastAPI hands off long-running work in two ways: it triggers n8n [webhooks](docs/Tech-Glossary.md#webhook) to sequence multi-step workflows, and n8n calls back into FastAPI's authenticated internal [API](docs/Tech-Glossary.md#api) to actually dispatch work. The heavy lifting — OCR, LLM extraction, [chunking](docs/Tech-Glossary.md#chunking), and [embedding](docs/Tech-Glossary.md#embedding) — runs as an [idempotent](docs/Tech-Glossary.md#idempotent) Celery task chain (`validate_file → run_ocr → extract_fields → generate_embeddings`) against Redis as the broker, with PostgreSQL (via the `pgvector` image) and local filesystem storage as the durable state. Per ADR-009, n8n owns sequencing, retries, and external integration visibility but never writes to application tables directly; FastAPI owns validation, auth, and authoritative document/review state; Celery owns the CPU- and I/O-heavy processing itself. [Docker Compose](docs/Tech-Glossary.md#docker-compose) runs the whole stack locally, including n8n's own bootstrap of its internal-API credential and workflow imports on container start.

## End-to-end flow, phase by phase

**Ingestion (Phase 1).** A user uploads a PDF in the React UI, which calls `POST /api/documents`. FastAPI validates the file, hashes and stores it, persists a `Document` row, and calls the `01-document-upload-ingestion` n8n workflow, which in turn calls the internal `POST /api/internal/documents/{id}/process` endpoint to dispatch the Celery chain.

**OCR (Phase 2).** `run_ocr` rasterizes each page with PyMuPDF and runs the configured OCR engine (PaddleOCR by default, swappable via `OCR_ENGINE`), persisting per-page text and confidence scores to `OcrPage` rows, upserted so re-OCR doesn't duplicate. Results are readable via `GET /api/documents/{id}/ocr`.

**AI extraction (Phase 3).** Once OCR completes, `extract_fields` sends the combined page text to the configured LLM provider (any OpenAI-compatible endpoint — OpenAI, Azure OpenAI, Ollama, vLLM) using a versioned [prompt](docs/Tech-Glossary.md#prompt), validates the returned [JSON](docs/Tech-Glossary.md#json) against a Pydantic schema (parties, dates, monetary values, key clauses, obligations), and persists it, exposed via `GET /api/documents/{id}/extraction`. Schema failures are terminal and logged; transport/LLM errors retry.

**Chunking and embedding (feeds Phase 5).** `generate_embeddings` chunks the OCR text with a configurable token limit and overlap, embeds each chunk via the configured embedding provider, and upserts into `chunks` — this runs as soon as extraction finishes, independent of review state.

**Review (Phase 4).** Reviewers open a completed document in the frontend and see the PDF, OCR text, and extracted fields side by side. Edits move the document through an explicit state machine (`draft_review → in_review → approved | rejected → archived`, with `rejected → draft_review` for revisions) backed by optimistic locking and an append-only `ReviewRevision`/[audit-log](docs/Tech-Glossary.md#audit-log) trail, via `/api/documents/{id}/review` and its `submit`/`approve`/`reject`/`revise`/`archive` actions.

**Search & [RAG](docs/Tech-Glossary.md#rag) (Phase 5).** A chunk only becomes searchable once its document's review is `approved` — enforced as a query-time join, not a gate on embedding generation. `GET /api/search` runs [hybrid retrieval](docs/Tech-Glossary.md#hybrid-search) (configurable lexical/vector weighting), and `POST /api/chat` retrieves the same way, builds a context block, and asks the LLM for an answer with citations built directly from the retrieved chunks. The `03-rag-chat` n8n workflow fronts the chat endpoint as an observable pipeline step.

**Resilience.** The `02-processing-watchdog` n8n workflow polls for documents stuck in `queued`/`processing`, and auto-retries `failed` documents (bounded by `DOCUMENT_AUTO_RETRY_MAX`) before surfacing anything that still needs a human via `/api/internal/documents/{id}/auto-retry` and `/reprocess`.

## Technology

- React + TypeScript + Vite
- FastAPI
- Celery
- n8n
- PostgreSQL
- Redis
- Docker Compose
- PyMuPDF
- Tesseract OCR
- OpenAI-compatible APIs / Ollama

## Repository

```text
apps/
  frontend/
  backend/

packages/
  api-client/

n8n/
infra/
docs/
fixtures/
```

## Running locally

### Requirements

- [Docker](docs/Tech-Glossary.md#docker) Desktop
- Docker Compose

### Start

```bash
docker compose up --build
```

### Stop

```bash
docker compose down
```

### Reset

```bash
docker compose down -v
```

### Phase 0 Verification

Run these checks after the stack is up:

```bash
make verify-phase0
```

### Backend Internal Auth Test

```bash
make test-backend-auth
```

### Environment Variables

Copy `.env.example` to `.env` and adjust values as needed.

| Variable | Purpose | Default |
| --- | --- | --- |
| APP_ENV | Backend runtime environment label | development |
| LOG_LEVEL | Backend and worker log verbosity | INFO |
| INTERNAL_API_KEY | Header value for internal API routes | change-me |
| POSTGRES_DB | Main PostgreSQL database name | contracts |
| POSTGRES_USER | PostgreSQL username | postgres |
| POSTGRES_PASSWORD | PostgreSQL password | postgres |
| DATABASE_URL | SQLAlchemy connection string for backend | postgresql+psycopg2://postgres:postgres@postgres:5432/contracts |
| CELERY_BROKER_URL | Redis broker URL for Celery | redis://redis:6379/0 |
| CELERY_RESULT_BACKEND | Redis result backend URL for Celery | redis://redis:6379/1 |
| VITE_API_BASE_URL | Frontend API base URL | <http://localhost:8000/api> |
| VITE_ENABLE_API_MOCKS | Dev-only mock of WS-02's `/documents` endpoints (Phase 1) until they ship; set to `false` once real endpoints exist | true |
| N8N_WEBHOOK_URL | Webhook the backend calls after upload to trigger the n8n ingestion workflow (WS-04) | <http://n8n:5678/webhook/document-uploaded> |
| N8N_WEBHOOK_TIMEOUT_SECONDS | Timeout for the upload-trigger webhook call | 5 |
| DOCUMENT_AUTO_RETRY_MAX | Max automatic retries the n8n watchdog (`02-processing-watchdog`) will trigger for a `failed` document via `/auto-retry` before it stops and surfaces it for a human | 3 |
| N8N_DB_HOST | n8n PostgreSQL host | postgres |
| N8N_DB_PORT | n8n PostgreSQL port | 5432 |
| N8N_DB_NAME | n8n PostgreSQL database name | n8n |
| N8N_DB_USER | n8n PostgreSQL username (dedicated role, isolated from POSTGRES_USER) | n8n |
| N8N_DB_PASSWORD | n8n PostgreSQL password (dedicated role, isolated from POSTGRES_PASSWORD) | n8n-change-me |
| N8N_HOST | n8n service host | localhost |
| N8N_PORT | n8n service port | 5678 |
| N8N_PROTOCOL | n8n protocol | http |
| N8N_SECURE_COOKIE | n8n secure cookie mode | false |
| GENERIC_TIMEZONE | n8n timezone | UTC |
| N8N_ENCRYPTION_KEY | n8n credential encryption key | replace-this-key |
| OCR_ENGINE | OCR engine implementation (ADR-010): `paddleocr` or `null` | paddleocr |
| OCR_RASTERIZE_DPI | Page rasterization DPI before OCR | 200 |
| OCR_MAX_RETRIES | Celery retry attempts for transient OCR failures | 3 |
| LLM_PROVIDER | LLM client implementation (ADR-012) | openai_compatible |
| LLM_BASE_URL | OpenAI-compatible LLM endpoint (OpenAI, Azure OpenAI, Ollama, vLLM); extraction fails fast if unset | (unset) |
| LLM_API_KEY | LLM provider API key | (unset) |
| LLM_MODEL | LLM model name | gpt-4o-mini |
| LLM_TIMEOUT_SECONDS | LLM request timeout | 60 |
| LLM_MAX_RETRIES | Celery retry attempts for transient LLM failures | 3 |
| EMBEDDING_PROVIDER | Embedding client implementation (ADR-017) | openai_compatible |
| EMBEDDING_BASE_URL | OpenAI-compatible embedding endpoint; embedding generation fails fast if unset | (unset) |
| EMBEDDING_API_KEY | Embedding provider API key | (unset) |
| EMBEDDING_MODEL | Embedding model name | text-embedding-3-small |
| EMBEDDING_TIMEOUT_SECONDS | Embedding request timeout | 30 |
| EMBEDDING_MAX_RETRIES | Celery retry attempts for transient embedding failures | 3 |
| CHUNK_TOKEN_LIMIT | Max tokens (whitespace-approximated) per chunk (ADR-018) | 500 |
| CHUNK_OVERLAP_TOKENS | Token overlap between consecutive chunks | 50 |
| SEARCH_KEYWORD_WEIGHT | Weight of the lexical signal in hybrid search ranking (ADR-019) | 0.4 |
| SEARCH_VECTOR_WEIGHT | Weight of the vector-similarity signal in hybrid search ranking (ADR-019) | 0.6 |
| SEARCH_DEFAULT_LIMIT | Default number of results from `GET /api/search` | 10 |
| CHAT_CONTEXT_CHUNKS | Number of retrieved chunks passed as context to `POST /api/chat` (ADR-020) | 5 |
| WORKER_CPU_LIMIT | celery-worker CPU limit (Phase 2: OCR is CPU-heavy) | 2 |
| WORKER_MEMORY_LIMIT | celery-worker memory limit | 4G |
| WORKER_CPU_RESERVATION | celery-worker CPU reservation | 0.5 |
| WORKER_MEMORY_RESERVATION | celery-worker memory reservation | 1G |

The `postgres` service runs the `pgvector/pgvector:pg16` image with the `vector` extension enabled on the application database (ADR-016), ready for WS-02/WS-03 to migrate `chunks.embedding` to a native `vector` column. The `n8n` service uses its own Postgres role (`N8N_DB_USER`/`N8N_DB_PASSWORD`), isolated from the application's credentials — both are provisioned by `infra/postgres-init.sh` on first boot of an empty `postgres_data` volume.

## Documentation

### Knowledge Base

- [[docs/MOC.md]]
- [Tech Glossary](docs/Tech-Glossary.md) — plain-English explanations of OCR, AI, RAG, and other terms used in this project, for non-technical readers.

### Planning

- MVP-plan.md
- MVP-plan-with-n8n.md
- High-Level-Implementation-Plan.md

### Progress

- docs/architecture/Progress.md

### Workstreams

- [Workstreams Overview](docs/workstreams/README.md)
- [WS-01 Frontend](docs/workstreams/WS-01-Frontend.md)
- [WS-02 Backend and Data](docs/workstreams/WS-02-Backend-and-Data.md)
- [WS-03 Document Processing and OCR](docs/workstreams/WS-03-Document-Processing-and-OCR.md)
- [WS-04 Workflow Orchestration](docs/workstreams/WS-04-Workflow-Orchestration.md)
- [WS-05 Infrastructure and DevOps](docs/workstreams/WS-05-Infrastructure-and-DevOps.md)
- [WS-06 Quality, Testing, and Documentation](docs/workstreams/WS-06-Quality-Testing-and-Documentation.md)

### Product Requirements

- [PRD-Phase-0-Foundation](docs/architecture/templates/PRD-Phase-0-Foundation.md)
- [PRD-Phase-1-Document-Ingestion](docs/architecture/templates/PRD-Phase-1-Document-Ingestion.md)
- [PRD-Phase-2-OCR-Pipeline](docs/architecture/templates/PRD-Phase-2-OCR-Pipeline.md)
- [PRD-Phase-3-AI-Extraction](docs/architecture/templates/PRD-Phase-3-AI-Extraction.md)
- [PRD-Phase-4-Contract-Review-UI](docs/architecture/templates/PRD-Phase-4-Contract-Review-UI.md)
- [PRD-Phase-5-Search-and-Knowledge-Base-RAG](docs/architecture/templates/PRD-Phase-5-Search-and-Knowledge-Base-RAG.md)

### Architecture Decision Records

**Foundation**

- [ADR-001 Monorepo](docs/architecture/templates/ADR-001-Monorepo.md)
- [ADR-002 Docker Compose](docs/architecture/templates/ADR-002-Docker-Compose.md)
- [ADR-003 Repository Structure](docs/architecture/templates/ADR-003-Repository-Structure.md)
- [ADR-004 FastAPI](docs/architecture/templates/ADR-004-FastAPI-as-Backend-Framework.md)
- [ADR-005 React + TypeScript + Vite](docs/architecture/templates/ADR-005-React-TypeScript-Vite.md)
- [ADR-006 PostgreSQL](docs/architecture/templates/ADR-006-PostgreSQL-as-Primary-Database.md)
- [ADR-007 Redis](docs/architecture/templates/ADR-007-Redis-as-Cache-and-Message-Broker.md)
- [ADR-008 Celery](docs/architecture/templates/ADR-008-Celery-for-Background-Processing.md)
- [ADR-009 n8n](docs/architecture/templates/ADR-009-n8n-for-Workflow-Orchestration.md)

**OCR & AI**

- [ADR-010 OCR Engine Selection](docs/architecture/templates/ADR-010-OCR-Engine-Selection.md)
- [ADR-011 OCR Storage Strategy](docs/architecture/templates/ADR-011-OCR-Storage-Strategy.md)
- [ADR-012 LLM Provider Selection](docs/architecture/templates/ADR-012-LLM-Provider-Selection.md)
- [ADR-013 Prompt Management Strategy](docs/architecture/templates/ADR-013-Prompt-Management-Strategy.md)

**Review & Audit**

- [ADR-014 Review State Management](docs/architecture/templates/ADR-014-Review-State-Management.md)
- [ADR-015 Audit Logging Strategy](docs/architecture/templates/ADR-015-Audit-Logging-Strategy.md)

**Search & RAG**

- [ADR-016 Vector Database Selection](docs/architecture/templates/ADR-016-Vector-Database-Selection.md)
- [ADR-017 Embedding Model Strategy](docs/architecture/templates/ADR-017-Embedding-Model-Strategy.md)
- [ADR-018 Document Chunking Strategy](docs/architecture/templates/ADR-018-Document-Chunking-Strategy.md)
- [ADR-019 Hybrid Retrieval Strategy](docs/architecture/templates/ADR-019-Hybrid-Retrieval-Strategy.md)
- [ADR-020 RAG Orchestration](docs/architecture/templates/ADR-020-RAG-Orchestration.md)

## Development Roadmap

| Phase | Description | [PRD](docs/Tech-Glossary.md#prd) |
|-------|-------------|-----|
| 0 | Foundation | [PRD-0](docs/architecture/templates/PRD-Phase-0-Foundation.md) |
| 1 | Document Ingestion | [PRD-1](docs/architecture/templates/PRD-Phase-1-Document-Ingestion.md) |
| 2 | OCR Pipeline | [PRD-2](docs/architecture/templates/PRD-Phase-2-OCR-Pipeline.md) |
| 3 | AI Extraction | [PRD-3](docs/architecture/templates/PRD-Phase-3-AI-Extraction.md) |
| 4 | Contract Review UI | [PRD-4](docs/architecture/templates/PRD-Phase-4-Contract-Review-UI.md) |
| 5 | Search & Knowledge Base (RAG) | [PRD-5](docs/architecture/templates/PRD-Phase-5-Search-and-Knowledge-Base-RAG.md) |

## License

TBD.

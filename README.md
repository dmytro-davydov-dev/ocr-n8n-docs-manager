# Contract Review MVP

An AI-assisted contract review application demonstrating a modern document-processing architecture using **React**, **FastAPI**, **Celery**, **n8n**, **PostgreSQL**, **Redis**, OCR, and LLMs.

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

- Docker Desktop
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
| N8N_DB_HOST | n8n PostgreSQL host | postgres |
| N8N_DB_PORT | n8n PostgreSQL port | 5432 |
| N8N_DB_NAME | n8n PostgreSQL database name | n8n |
| N8N_DB_USER | n8n PostgreSQL username | postgres |
| N8N_DB_PASSWORD | n8n PostgreSQL password | postgres |
| N8N_HOST | n8n service host | localhost |
| N8N_PORT | n8n service port | 5678 |
| N8N_PROTOCOL | n8n protocol | http |
| N8N_SECURE_COOKIE | n8n secure cookie mode | false |
| GENERIC_TIMEZONE | n8n timezone | UTC |
| N8N_ENCRYPTION_KEY | n8n credential encryption key | replace-this-key |

## Documentation

### Knowledge Base

- [[docs/MOC.md]]

### Planning

- MVP-plan.md
- MVP-plan-with-n8n.md
- High-Level-Implementation-Plan.md

### Progress

- docs/architecture/Progress.md

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

| Phase | Description | PRD |
|-------|-------------|-----|
| 0 | Foundation | [PRD-0](docs/architecture/templates/PRD-Phase-0-Foundation.md) |
| 1 | Document Ingestion | [PRD-1](docs/architecture/templates/PRD-Phase-1-Document-Ingestion.md) |
| 2 | OCR Pipeline | [PRD-2](docs/architecture/templates/PRD-Phase-2-OCR-Pipeline.md) |
| 3 | AI Extraction | [PRD-3](docs/architecture/templates/PRD-Phase-3-AI-Extraction.md) |
| 4 | Contract Review UI | [PRD-4](docs/architecture/templates/PRD-Phase-4-Contract-Review-UI.md) |
| 5 | Search & Knowledge Base (RAG) | [PRD-5](docs/architecture/templates/PRD-Phase-5-Search-and-Knowledge-Base-RAG.md) |

## License

TBD.

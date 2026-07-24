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

- docs/architecture/templates/PRD-Phase-0-Foundation.md
- docs/architecture/templates/PRD-Phase-1-Document-Ingestion.md

### Architecture Decision Records

- ADR-001 Monorepo
- ADR-002 Docker Compose
- ADR-003 Repository Structure
- ADR-004 FastAPI
- ADR-005 React
- ADR-006 PostgreSQL
- ADR-007 Redis
- ADR-008 Celery
- ADR-009 n8n

## Development Roadmap

1. Foundation
2. Upload & Storage
3. n8n Orchestration
4. Native PDF Extraction
5. OCR
6. AI Extraction
7. Review Workspace
8. Hardening

## License

TBD.

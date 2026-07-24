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

- PRD-Phase-0-Foundation.md
- PRD-Phase-1-Upload.md
- PRD-Phase-2-Orchestration.md
- PRD-Phase-3-PDF.md
- PRD-Phase-4-OCR.md
- PRD-Phase-5-AI.md
- PRD-Phase-6-Review.md
- PRD-Phase-7-Hardening.md

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

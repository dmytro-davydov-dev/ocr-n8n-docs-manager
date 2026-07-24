# Progress

_Last updated:_ 2026-07-24 (WS-01 Phase 2 OCR viewer)

## Overall Status

- **Current Phase:** Phase 0 – Foundation
- **Overall Progress:** 100%
- **Project Status:** 🟢 On Track

---

# Phase Tracker

| Phase | Status | Progress | PRD | ADRs |
|---|---|---:|---|---|
| Phase 0 – Foundation | ✅ | 100% | [[templates/PRD-Phase-0-Foundation\|PRD-0]] | ADR-001 to ADR-009 |
| Phase 1 – Document Ingestion | ☐ | 0% | [[templates/PRD-Phase-1-Document-Ingestion\|PRD-1]] | — |
| Phase 2 – OCR Pipeline | ☐ | 0% | [[templates/PRD-Phase-2-OCR-Pipeline\|PRD-2]] | ADR-010, ADR-011 |
| Phase 3 – AI Extraction | ☐ | 0% | [[templates/PRD-Phase-3-AI-Extraction\|PRD-3]] | ADR-012, ADR-013 |
| Phase 4 – Contract Review UI | ☐ | 0% | [[templates/PRD-Phase-4-Contract-Review-UI\|PRD-4]] | ADR-014, ADR-015 |
| Phase 5 – Search & RAG | ☐ | 0% | [[templates/PRD-Phase-5-Search-and-Knowledge-Base-RAG\|PRD-5]] | ADR-016 to ADR-020 |

---

# Current Sprint

## Goals

- Establish monorepo scaffolding for frontend, backend, shared package, and infra.
- Make the local stack runnable through Docker Compose.

## Completed

- Created monorepo structure: `apps/`, `packages/`, `infra/`, `n8n/`, `fixtures/`.
- Implemented FastAPI shell with `/api/health` endpoint and config/logging/database modules.
- Added Alembic setup and initial migration (`0001_init`) for baseline schema.
- Added Celery app scaffold and Redis wiring.
- Implemented React + TypeScript + Vite shell with Material UI, Router, React Query, and error boundary.
- Added shared API client package used by frontend.
- Added `docker-compose.yml`, backend/frontend Dockerfiles, `.env.example`, `.gitignore`, and `Makefile`.
- Verified compose file structure with `docker compose config`.
- Verified backend syntax with `python3 -m compileall apps/backend`.
- Added backend internal API key checks for internal endpoints (`/api/internal/ping`).
- Added n8n container health check (`/healthz`) in Compose.
- Added `make verify-phase0` acceptance-check target for stack health and connectivity checks.
- Added backend auth regression test (`apps/backend/tests/test_internal_api_auth.py`) and `make test-backend-auth` command.
- Parameterized PostgreSQL and n8n service configuration via `.env` values in Compose.
- Documented environment variables in README and expanded `.env.example` coverage.
- Resolved Docker Desktop daemon/storage corruption by recreating Docker VM disk image and restarting backend.
- Completed first full-stack startup verification with `docker compose up --build -d`.
- Passed `make verify-phase0` acceptance checks (frontend, backend, n8n, postgres, redis, celery).
- Passed backend internal auth regression tests via `make test-backend-auth`.

## In Progress

- WS-01 Frontend: Phase 1 upload UI. Added drag-and-drop upload with per-file
  progress, a live-polling document list, and `/documents` types/methods in
  `packages/api-client` (list/get/upload), per PRD-Phase-1 FR-101–108.
  WS-02 hasn't implemented the `/documents` endpoints yet, so a dev-only mock
  (`apps/frontend/src/mocks/mockDocumentsApi.ts`, gated by
  `VITE_ENABLE_API_MOCKS`) stands in for the contract in the interim.
- Repo hygiene: removed stray build artifacts (`tsconfig.tsbuildinfo`,
  `vite.config.ts.timestamp-*.mjs`) that were accidentally committed with the
  Phase 1 frontend work, and added `.gitignore` rules so they don't recur.
- WS-01 Frontend: Phase 2 OCR viewer. Added `OcrPage` type and
  `getOcrPages`/`getDocumentFile` methods to `packages/api-client` per
  ADR-011's page-level record shape. Added `/documents/:id` detail route with
  a PDF viewer (object-URL iframe) synced to a per-page OCR text panel with
  color-coded confidence chips. Extended the dev-only mock to store uploaded
  file blobs and generate placeholder OCR pages once a document reaches
  `complete`, since WS-02/WS-03 haven't shipped the real OCR pipeline yet.
  Verified with `tsc -b` and `vite build`.

## Blockers

- None.

## Risks

- Docker VM disk growth may reintroduce local storage pressure over time if not periodically pruned.

## Technical Debt

- Add richer initial schema and model coverage once Phase 1 starts.

## Open Questions

- Should we pin image digests for reproducible local builds in addition to tags?

## Architecture Decisions

- [[templates/ADR-001-Monorepo|ADR-001 Monorepo]]
- [[templates/ADR-002-Docker-Compose|ADR-002 Docker Compose]]
- [[templates/ADR-003-Repository-Structure|ADR-003 Repository Structure]]
- [[templates/ADR-004-FastAPI-as-Backend-Framework|ADR-004 FastAPI]]
- [[templates/ADR-005-React-TypeScript-Vite|ADR-005 React + TypeScript + Vite]]
- [[templates/ADR-006-PostgreSQL-as-Primary-Database|ADR-006 PostgreSQL]]
- [[templates/ADR-007-Redis-as-Cache-and-Message-Broker|ADR-007 Redis]]
- [[templates/ADR-008-Celery-for-Background-Processing|ADR-008 Celery]]
- [[templates/ADR-009-n8n-for-Workflow-Orchestration|ADR-009 n8n]]
- [[templates/ADR-010-OCR-Engine-Selection|ADR-010 OCR Engine]]
- [[templates/ADR-011-OCR-Storage-Strategy|ADR-011 OCR Storage]]
- [[templates/ADR-012-LLM-Provider-Selection|ADR-012 LLM Provider]]
- [[templates/ADR-013-Prompt-Management-Strategy|ADR-013 Prompt Management]]
- [[templates/ADR-014-Review-State-Management|ADR-014 Review State]]
- [[templates/ADR-015-Audit-Logging-Strategy|ADR-015 Audit Logging]]
- [[templates/ADR-016-Vector-Database-Selection|ADR-016 Vector Database]]
- [[templates/ADR-017-Embedding-Model-Strategy|ADR-017 Embedding Model]]
- [[templates/ADR-018-Document-Chunking-Strategy|ADR-018 Document Chunking]]
- [[templates/ADR-019-Hybrid-Retrieval-Strategy|ADR-019 Hybrid Retrieval]]
- [[templates/ADR-020-RAG-Orchestration|ADR-020 RAG Orchestration]]

## Next Milestone

Phase 1 kickoff: Document Ingestion foundation.

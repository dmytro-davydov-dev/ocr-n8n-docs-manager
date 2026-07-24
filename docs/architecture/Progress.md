# Progress

_Last updated:_ 2026-07-24 (WS-02 Phase 1 document ingestion backend)

## Overall Status

- **Current Phase:** Phase 1 – Document Ingestion
- **Overall Progress:** 27%
- **Project Status:** 🟢 On Track

---

# Phase Tracker

| Phase | Status | Progress | PRD | ADRs |
|---|---|---:|---|---|
| Phase 0 – Foundation | ✅ | 100% | [[templates/PRD-Phase-0-Foundation\|PRD-0]] | ADR-001 to ADR-009 |
| Phase 1 – Document Ingestion | 🔶 | 60% | [[templates/PRD-Phase-1-Document-Ingestion\|PRD-1]] | — |
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

- WS-02 Backend: Phase 1 document ingestion. Implemented `Document` and
  append-only `AuditLog` SQLAlchemy models, a local-filesystem storage
  service (`/documents` volume, sha256 content hash), and a
  service/repository layer that enforces legal document-status transitions
  (`uploaded -> queued -> processing -> complete|failed`) and writes an
  audit-log entry for every mutation, per ADR-006/ADR-015. Added real
  `POST/GET /api/documents`, `GET /api/documents/{id}`,
  `GET /api/documents/{id}/file` endpoints matching the contract WS-01
  already built its mock against (`DocumentSummary` camelCase JSON), plus
  an internal `PATCH /api/internal/documents/{id}/status` callback for
  WS-04 (n8n) to report processing progress — n8n still cannot write to
  application tables directly. Added Alembic migration `0002` replacing
  the Phase-0 placeholder schema. Added 11 passing unit tests
  (`apps/backend/tests/test_documents_api.py`, SQLite-backed,
  `make test-backend`) and OpenAPI export/drift-check scripts + a
  `backend` GitHub Actions workflow wired to `make verify-openapi`,
  addressing the WS-02 Done Criteria's "OpenAPI is generated and
  versioned; CI detects contract drift" bullet. Pinned `pydantic==2.9.2`
  and added the previously-missing `python-multipart` dependency (required
  by FastAPI for file uploads; its absence would have made the upload
  endpoint 500 at runtime).
- WS-02 Backend: review state machine (ADR-014), built to close out the
  WS-02 Done Criteria. Added `Review` (status/version/content) and
  append-only `ReviewRevision` models plus a migration (`0003`). The
  status machine enforces every ADR-014 transition explicitly (no boolean
  `approved` flag): `draft_review -> in_review -> approved|rejected`,
  `rejected -> draft_review|archived`, `approved -> archived`. Editing is
  optimistic-locked via a `version` counter (`ReviewVersionConflict` ->
  HTTP 412) and every edit/transition appends a `ReviewRevision` snapshot
  (ADR-014: "user edits create a new review version while preserving the
  original AI output") plus an `audit_log` entry. Approving with empty
  content and rejecting without a reason are rejected as validation
  errors (422). Added `POST/GET/PATCH /api/documents/{id}/review`,
  `POST .../review/{submit,approve,reject,archive}`, and
  `GET .../review/history` (the Phase-4 audit-history API deliverable).
  11 new passing tests in `apps/backend/tests/test_reviews_api.py`
  (22 total across the backend test suite).

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

- WS-04 has not shipped the n8n upload workflow yet (`n8n/` is empty), so
  `N8N_WEBHOOK_URL` has no real receiver. Every upload against the real
  backend currently ends in `status: "failed"` with
  `errorMessage: "Failed to trigger processing workflow"` rather than
  advancing to `queued`/`processing`/`complete` — this is intentional
  (FR-105's trigger step genuinely fails) and will resolve once WS-04
  delivers the workflow.
- `apps/frontend/src/mocks/mockDocumentsApi.ts` (gated by
  `VITE_ENABLE_API_MOCKS`) is still in place; WS-02's real `/documents`
  endpoints now exist but WS-01 owns the decision of when to retire the
  mock and point the frontend at them end-to-end.
- The `Review`/`ReviewRevision` state machine (ADR-014) was implemented
  ahead of Phase 2/3 (OCR, extraction) to satisfy WS-02's Done Criteria,
  since those phases don't exist yet. `POST /api/documents/{id}/review`
  currently takes a caller-supplied `content` payload as a stand-in for
  real AI-extracted data; once Phase 3 ships, extraction becomes the seed
  for the initial draft instead (`review_service.start_review`'s docstring
  flags this). The review API itself (transitions, optimistic locking,
  append-only revision history, audit log) is real and fully tested, not
  a placeholder.
- No frontend consumes the review endpoints yet — WS-01's UI for this is
  PRD-Phase-4 (Contract Review UI) scope, not started.
- `packages/api-client/openapi.json` is a generated artifact checked in by
  `make export-openapi`; the hand-written TS client in
  `packages/api-client/src/index.ts` is not yet generated _from_ it (still
  a manually-kept mirror of the same contract).

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

# Progress

_Last updated:_ 2026-07-24 (WS-05 infrastructure/DevOps: env-var plumbing fix, celery-worker resource limits, pgvector-enabled Postgres, isolated n8n credentials — WS-05 Done Criteria met)

## Overall Status

- **Current Phase:** Phase 1 – Document Ingestion
- **Overall Progress:** 45%
- **Project Status:** 🟢 On Track

---

# Phase Tracker

| Phase | Status | Progress | PRD | ADRs |
|---|---|---:|---|---|
| Phase 0 – Foundation | ✅ | 100% | [[templates/PRD-Phase-0-Foundation\|PRD-0]] | ADR-001 to ADR-009 |
| Phase 1 – Document Ingestion | 🔶 | 80% | [[templates/PRD-Phase-1-Document-Ingestion\|PRD-1]] | — |
| Phase 2 – OCR Pipeline | 🔶 | 75% | [[templates/PRD-Phase-2-OCR-Pipeline\|PRD-2]] | ADR-010, ADR-011 |
| Phase 3 – AI Extraction | 🔶 | 65% | [[templates/PRD-Phase-3-AI-Extraction\|PRD-3]] | ADR-012, ADR-013 |
| Phase 4 – Contract Review UI | ☐ | 0% | [[templates/PRD-Phase-4-Contract-Review-UI\|PRD-4]] | ADR-014, ADR-015 |
| Phase 5 – Search & RAG | 🔶 | 30% | [[templates/PRD-Phase-5-Search-and-Knowledge-Base-RAG\|PRD-5]] | ADR-016 to ADR-020 |

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
- WS-03 Processing/AI: Celery task layer (`apps/backend/app/tasks/`), closing
  out the WS-03 Phase 0/1/2 milestones. Added `documents.validate_file`
  (Phase 1 — opens the stored PDF with PyMuPDF to catch truncated/corrupt
  files a content-type check alone would miss) and `documents.run_ocr`
  (Phase 2 — rasterizes each page via PyMuPDF, runs the configured OCR
  engine, and persists results page-by-page). Both tasks follow ADR-008's
  task contract: identifiers-only payloads (`document_id`), state read from
  the `documents` row before acting (idempotent no-op on documents already
  past the expected status), transient failures (`self.retry`, e.g. storage
  or OCR-provider errors) kept distinct from terminal ones (bad PDF, missing
  native dependency -> `failed` with `error_message`), and durable outcomes
  written only through the service layer (`document_repository`,
  `ocr_service`), never raw model writes from a task. Added `OcrPage`
  (ADR-011: document_id/page_number/extracted_text/confidence_score/
  processing_timestamp/ocr_engine_version, unique on
  `(document_id, page_number)` so re-OCRing a page upserts instead of
  duplicating) with migration `0004_ocr_pages`, plus `GET
  /api/documents/{id}/ocr` — the endpoint `packages/api-client`'s
  `getOcrPages` already expected, matching the `OcrPage` TS interface
  field-for-field. OCR engine selection is provider-agnostic
  (`app/services/ocr_engine.py`): an `OcrEngine` protocol, a `PaddleOcrEngine`
  (ADR-010, lazy-imports `paddleocr` so the heavy native dependency isn't
  required just to import the module) and a `NullOcrEngine`, chosen purely by
  the `OCR_ENGINE` config value — no code change needed to swap engines,
  per the WS-03 Done Criteria. 8 new passing tests
  (`apps/backend/tests/test_ocr_pipeline.py`, 30 total across the backend
  suite) cover idempotency under simulated duplicate/retried delivery,
  retry-vs-terminal failure classification, and the `/ocr` response
  contract, using a fake `OcrEngine` injected into the task (paddleocr
  itself was not runnable in this dev shell — see Technical Debt).
- WS-03 Processing/AI: extraction + chunking/embedding tasks, closing the
  WS-03 Done Criteria's last open bullet ("OCR engine, LLM provider, and
  embedding model are all swappable via configuration"). Added
  `documents.extract_fields` (Phase 3): runs once a document is `complete`
  (OCR done), concatenates its `OcrPage` text, calls the configured
  `LlmProvider` with a versioned prompt file
  (`app/prompts/contract_extraction_v1.md`, ADR-013: front-matter records
  `prompt_id`/`prompt_version`), and validates the JSON response against a
  Pydantic schema (`ExtractedContractFields` — parties, dates, monetary
  values, key clauses, obligations per PRD-3) before persisting it to a new
  `extractions` table (migration `0005`, one row per document, upserted —
  idempotent). Schema-validation failures are logged and treated as
  terminal (FR-303/304, deterministic for the same input); LLM/network
  errors go through `self.retry`. Added `documents.generate_embeddings`
  (Phase 5's pipeline slice — WS-03 owns chunking/embedding generation
  only, not the search/chat APIs, which are out of this workstream's
  scope): chunks each document's OCR text with configurable token
  limit/overlap and page/offset metadata (`app/services/chunking.py`,
  ADR-018), embeds each chunk via the configured `EmbeddingProvider`, and
  upserts into a new `chunks` table (migration `0006`, unique on
  `document_id`+`chunk_index`; any chunk left over from a prior run with a
  different config is dropped via `chunk_repository.delete_from_index`).
  Both new providers (`app/services/llm_provider.py`,
  `app/services/embedding_provider.py`) follow the same shape as
  `OcrEngine`: a single OpenAI-compatible HTTP client (ADR-012/017 — this
  covers OpenAI, Azure OpenAI, Ollama, and vLLM through one implementation,
  since they all speak the same API) selected via `LLM_PROVIDER`/
  `EMBEDDING_PROVIDER`, swappable by config alone. Added
  `GET /api/documents/{id}/extraction` and `GET /api/documents/{id}/chunks`.
  9 new passing tests (`apps/backend/tests/test_ai_pipeline.py`, 39 total
  across the backend suite) cover idempotency, retry-vs-terminal
  classification (including schema-validation failures), and stale-chunk
  cleanup, using fake providers injected into the tasks — neither task has
  been run against a live LLM/embedding endpoint (see Technical Debt).

- WS-04 n8n: workflow orchestration (ADR-009), closing WS-04's Phase 0/1
  milestones and most of Phase 2/3. Added the internal endpoint n8n needed
  but that didn't exist yet, `POST /api/internal/documents/{id}/process`
  (`apps/backend/app/api/internal.py`) -- dispatches a Celery `chain`
  (`validate_file -> run_ocr -> extract_fields -> generate_embeddings`) so
  n8n never touches the Celery broker or application tables directly, only
  WS-02's authenticated internal API (WS-04's core constraint). Dispatch is
  safe under retry/duplicate calls for free: every task in the chain
  already re-checks the document's current status before acting (WS-03's
  idempotency design), so re-dispatching against a document that's already
  mid-pipeline or done just runs a chain of no-ops. 3 new passing tests
  (`apps/backend/tests/test_internal_processing.py`, 42 total across the
  backend suite) cover auth, 404, and the dispatched chain (mocked, no
  broker needed). Verified live against the real stack too: dispatched the
  chain through the actual Redis broker/Celery worker via
  `docker compose up` and confirmed in worker logs that all four tasks ran
  in order and no-op'd cleanly on an already-`failed` document.
  Added `n8n/workflows/` (previously empty) with three version-controlled
  workflow exports: `00-internal-api-smoke-test.json` (Phase 0 -- manual
  trigger calling the authenticated `/internal/ping` endpoint, satisfying
  the literal Phase 0 milestone), `01-document-upload-ingestion.json`
  (Phase 1 -- the webhook `N8N_WEBHOOK_URL`/`document_service.py` already
  called with no receiver; now calls `/process` and responds), and
  `02-processing-watchdog.json` (Phase 2/3 -- polls `GET /api/documents`
  every 10 min and surfaces `failed`/stuck documents in n8n's execution
  history for escalation). All three were validated by importing them into
  a real n8n 1.71.3 instance (`n8n import:workflow`), not just JSON-parsed.
  Wired `docker-compose.yml`'s `n8n` service to auto-import
  `n8n/workflows/` on every container start (`n8n import:workflow
  --separate && exec n8n`), so the committed JSON is enforced as the
  source of truth on restart rather than the runtime silently drifting
  from it (WS-04 Done Criteria). No real credentials appear in the
  exports -- HTTP Request nodes reference an `Internal API Key` credential
  by id/name only; the actual header value is entered by hand in the n8n
  UI post-import (documented in `n8n/workflows/README.md`, along with why
  n8n auto-deactivates `01`/`02` on first boot until that credential
  exists).
  The watchdog deliberately does not auto-retry failed documents: doing so
  would silently no-op today, since there's no `failed`/`complete` ->
  requeue transition in `document_repository.ALLOWED_TRANSITIONS` (see
  Technical Debt) -- it only surfaces them, which is honest about what's
  actually safe to automate right now versus faking a retry that wouldn't
  work.

- WS-05 Infrastructure/DevOps: closed out all of WS-05's Done Criteria and
  its remaining Phase 2/3/5 milestones. Found and fixed a real bug while
  auditing the compose file against WS-03's `Settings` class: `OCR_ENGINE`,
  `LLM_*`, `EMBEDDING_*`, `CHUNK_*`, `DOCUMENTS_STORAGE_PATH`, and
  `N8N_WEBHOOK_URL`/`_TIMEOUT_SECONDS` were documented in `.env.example` and
  the README table but never forwarded into the `backend`/`celery-worker`
  containers' `environment:` blocks in `docker-compose.yml` -- Pydantic's
  `Settings(env_file=".env")` only reads a `.env` file that doesn't exist
  inside those containers (the root `.env` isn't copied into the
  `apps/backend` build context), so every one of those settings was silently
  falling back to its code default regardless of what operators put in
  `.env`. Editing `.env` and restarting the stack did nothing for OCR
  engine/LLM/embedding provider selection until this was fixed -- this
  directly blocked the WS-05 Phase 3 milestone ("LLM/embedding provider
  credentials and endpoints configurable via env, no code changes"), which
  was previously true only in the Python code, not in the running compose
  stack. Added `cpus`/`memory` limits (`deploy.resources`, configurable via
  new `WORKER_CPU_LIMIT`/`WORKER_MEMORY_LIMIT`/*_RESERVATION env vars) to
  `celery-worker`, closing the Phase 2 milestone ("OCR engine resourced").
  Switched the `postgres` service to the `pgvector/pgvector:pg16` image and
  added `infra/postgres-init.sh` (replacing `postgres-init.sql`) which runs
  `CREATE EXTENSION IF NOT EXISTS vector` on the app database, closing the
  Phase 5 milestone ("pgvector extension enabled; vector indexes
  creatable") -- verified by creating a real `vector(3)` column with an
  `hnsw` index and running a `<->` similarity query against it (scratch
  table, dropped after). The same init script also gives n8n its own
  Postgres role (`N8N_DB_USER`/`N8N_DB_PASSWORD`, defaulting to
  `n8n`/`n8n-change-me`) with `CONNECT` revoked on the app database and
  vice versa, closing the WS-05 Done Criteria bullet "Application and n8n
  persistence are isolated (separate DB/schema/credentials)" -- previously
  n8n and the app shared the same Postgres user/password and only the
  database name differed. Applied all of this to the already-running local
  dev stack without a volume wipe: enabled the extension and locked down
  `CONNECT` on the live `contracts` db, then created the `n8n` role and
  reassigned ownership of all 33 existing tables/6 sequences/the `public`
  schema in the live `n8n` database to it (per-object `ALTER ... OWNER TO`,
  since `REASSIGN OWNED BY postgres` fails on Postgres's bootstrap
  superuser role) -- the n8n instance's existing workflows/credentials
  (including the manually-configured `Internal API Key` credential from
  WS-04, see Technical Debt) were preserved, not reset. Verified end-to-end
  against the live stack: `make verify-phase0` (unchanged, still green),
  a new `make verify-infra` target (pgvector extension present, n8n
  connects with its own role, n8n's role is denied `CONNECT` on the app
  db), and the full 42-test backend suite (`make test-backend`), all
  passing. Updated the README env var table and `.env.example` with the
  newly-plumbed and newly-added variables.

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

- WS-04's upload workflow (`n8n/workflows/01-document-upload-ingestion.json`)
  now exists and is exported `active: true`, but n8n auto-deactivates any
  imported workflow whose referenced credential doesn't exist yet -- so on
  a fresh instance (including a freshly `docker compose up`'d one) it
  imports inactive until an operator manually creates the `Internal API
  Key` HTTP Header Auth credential in the n8n UI and reactivates it (see
  `n8n/workflows/README.md`; this is a one-time step, same as any other
  secret that can't be committed). Until that's done, every upload still
  ends in `status: "failed"` with
  `errorMessage: "Failed to trigger processing workflow"`, same symptom as
  before WS-04 shipped anything -- don't mistake it for a regression.
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
- WS-03's Celery tasks now have a real dispatcher (WS-04's
  `POST /api/internal/documents/{id}/process`, see WS-04 entry above under
  Completed), but a document only reaches that endpoint via n8n's upload
  workflow, which needs the `Internal API Key` credential created by hand
  first (see the WS-04 bullet below). Until that one-time step is done in
  a given environment, a document can still reach `queued` but nothing
  moves it to `processing`/`complete` outside of a test or a manual
  `curl` calling `/process` directly.
- `paddleocr`/`paddlepaddle` were added to `apps/backend/requirements.txt`
  per ADR-010 but could not be installed/exercised in this dev shell
  (native build deps unavailable outside Docker); `PaddleOcrEngine` is
  implemented with a lazy import specifically so this doesn't block testing,
  but it has only been verified via `python -m compileall`, not a real OCR
  run. That needs a pass in the actual `celery-worker` container before
  Phase 2 can be called done end-to-end.
- `documents.extract_fields` and `documents.generate_embeddings` are
  implemented and unit-tested with fake providers, but neither has been run
  against a real OpenAI-compatible endpoint — `LLM_BASE_URL`/
  `EMBEDDING_BASE_URL` are unset by default (see `.env.example`), so both
  tasks currently return `"provider_unavailable"` and leave the document's
  `extractions`/`chunks` rows untouched until an operator points them at a
  real or self-hosted (e.g. Ollama) endpoint. This is the same
  fail-fast-over-silent-fallback posture as `OCR_ENGINE`.
- `chunks.embedding` is stored as a JSON float array, not a native
  `pgvector` column, even though ADR-016 selects pgvector. WS-05 now
  provisions the `vector` extension (`postgres` runs
  `pgvector/pgvector:pg16`, verified with a real `vector(3)`/`hnsw` probe —
  see WS-05 entry above under Completed), so this is no longer blocked on
  infra. A JSON column still keeps the model portable to the SQLite test
  database this suite runs against, so swapping in a real `Vector` column
  (and an ANN index, plus a decision on whether to keep SQLite-compatible
  tests or move them onto Postgres) is a WS-02/WS-03 follow-up migration,
  not further WS-05 work — Phase 5's actual search/retrieval API (out of
  WS-03's scope regardless, see PRD-5) will need it.
- The document status state machine (`document_repository.ALLOWED_TRANSITIONS`)
  has no transition back out of `complete`/`failed`, so there is currently
  no supported way to re-run OCR on an already-processed document even
  though `ocr_repository.upsert_page` is idempotent and would handle it
  correctly if reached. ADR-011 anticipates reprocessing as a benefit of the
  page-level storage model; wiring an actual retry/reprocess transition is
  unstarted.

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

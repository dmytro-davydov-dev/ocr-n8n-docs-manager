# Progress

_Last updated:_ 2026-07-25 (Phase 5: hybrid Search API and RAG Chat API with citations, backend-complete and tested)

## Overall Status

- **Current Phase:** Phase 5 – Search & RAG
- **Overall Progress:** 55%
- **Project Status:** 🟢 On Track

---

# Phase Tracker

| Phase | Status | Progress | PRD | ADRs |
|---|---|---:|---|---|
| Phase 0 – Foundation | ✅ | 100% | [[templates/PRD-Phase-0-Foundation\|PRD-0]] | ADR-001 to ADR-009 |
| Phase 1 – Document Ingestion | 🔶 | 85% | [[templates/PRD-Phase-1-Document-Ingestion\|PRD-1]] | — |
| Phase 2 – OCR Pipeline | 🔶 | 80% | [[templates/PRD-Phase-2-OCR-Pipeline\|PRD-2]] | ADR-010, ADR-011 |
| Phase 3 – AI Extraction | 🔶 | 75% | [[templates/PRD-Phase-3-AI-Extraction\|PRD-3]] | ADR-012, ADR-013 |
| Phase 4 – Contract Review UI | 🔶 | 60% | [[templates/PRD-Phase-4-Contract-Review-UI\|PRD-4]] | ADR-014, ADR-015 |
| Phase 5 – Search & RAG | 🔶 | 65% | [[templates/PRD-Phase-5-Search-and-Knowledge-Base-RAG\|PRD-5]] | ADR-016 to ADR-020 |

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

- WS-06 Quality/Testing/Documentation: closed out the WS-06 Done Criteria.
  Fixed ADR-001 and ADR-002, the only two ADRs still carrying a
  `YYYY-MM-DD` placeholder `Date` instead of an actual one (every other
  ADR/PRD already had Status/Date/Related Documents current; `docs/MOC.md`
  already linked every ADR/PRD/workstream doc, so no changes were needed
  there). Closed the Done Criteria's "CI blocks merges on... migration
  errors" gap: `.github/workflows/backend.yml` previously ran tests and an
  OpenAPI-drift check but never applied a migration, so a broken Alembic
  migration or a model that had drifted from what the migrations actually
  create would pass CI silently. Added a `pgvector/pgvector:pg16` service
  container to the workflow plus `alembic upgrade head` and `alembic check`
  steps. Running this locally against a real (throwaway) Postgres container
  before wiring it into CI immediately caught a real bug, not a
  hypothetical one: six indexes that migrations `0002`-`0006` create with
  `op.create_index(...)` (`ix_documents_status`, `ix_documents_content_hash`,
  `ix_audit_log_entity`, `ix_reviews_status`, `ix_review_revisions_review_id`,
  `ix_ocr_pages_document_id`, `ix_chunks_document_id`) were never declared
  on the corresponding SQLAlchemy model columns, so `alembic check` flagged
  them as drift an autogenerate would silently drop. Added the matching
  `index=True`/`Index(...)` declarations to the `Document`, `AuditLog`,
  `Review`, `ReviewRevision`, `OcrPage`, and `Chunk` models so the ORM
  layer matches the schema Alembic actually produces; verified clean with
  `alembic check` against a fresh Postgres and confirmed the existing
  42-test suite still passes unchanged. Populated `fixtures/` (previously
  empty, despite being a named WS-06 deliverable) with an
  `ocr_extraction/` regression fixture set closing the Phase 2/3 milestones:
  a synthetic 2-page PDF (`sample_contract.pdf`, fabricated contract text,
  not a real document) plus checked-in golden `sample_contract.ocr.json`/
  `sample_contract.extraction.json` files pinning the exact OCR-page and
  `ExtractedContractFields` output the pipeline should reproduce for it —
  a prompt/schema-regression baseline per ADR-013, refreshed in the same PR
  as any OCR engine/LLM/prompt change (`fixtures/README.md`).
  `apps/backend/tests/test_regression_fixtures.py` (new) replays those
  golden files through the real `validate_file -> run_ocr -> extract_fields`
  task chain via fixture-backed fake engine/provider (paddleocr/a real LLM
  still aren't runnable in this dev shell, see Technical Debt) and asserts
  the persisted API responses match the fixture exactly. Closed the Phase 1
  milestone "Ingestion integration tests (upload -> metadata -> workflow
  trigger)" with `apps/backend/tests/test_ingestion_integration.py` (new):
  unlike the existing per-task unit tests or `test_internal_processing.py`
  (which mocks `chain` itself and never runs real task logic), this test
  drives the actual seam end to end in one run — real `POST /api/documents`
  upload, asserts the outbound n8n workflow-trigger webhook (WS-04) was
  called with the right document id, calls the real internal `/process`
  endpoint (ADR-009), and runs the real `validate_file`/`run_ocr`/
  `extract_fields`/`generate_embeddings` task chain synchronously (OCR/LLM/
  embedding providers faked, everything else real) — then asserts the
  document reaches `complete` with OCR pages, extraction, and chunks all
  populated and retrievable. Full backend suite: 44 tests passing
  (`make test-backend`).

- Phase 5 (WS-02/WS-03): hybrid Search API and RAG Chat API, closing most of
  PRD-5's Backend deliverables (FR-503/504/505/506/507). Added
  `app/services/search_service.py` (`hybrid_search`, ADR-019): combines a
  portable lexical signal (term-frequency substring match — works
  identically against Postgres and the SQLite test DB, so no
  Postgres-only `tsvector` dependency was introduced) with a
  vector-similarity signal (cosine similarity over the existing JSON-stored
  chunk embeddings — see Technical Debt on why that's not a native pgvector
  column yet) into one configurable score
  (`SEARCH_KEYWORD_WEIGHT`/`SEARCH_VECTOR_WEIGHT`). Critically, FR-501
  ("Approved contracts are indexed") is enforced as a query-time filter
  (`searchable_chunks` inner-joins `Chunk -> Document -> Review` on
  `Review.status == 'approved'`), not by changing when embeddings are
  generated — `generate_embeddings` still runs as soon as OCR/extraction
  finish (WS-03's existing pipeline, independent of review state), so a
  chunk exists but is simply unreachable through search/chat until its
  document's review is approved. This was a deliberate scope choice to
  avoid touching the already-tested ingestion chain. Added
  `app/services/rag_service.py` (`answer_question`, ADR-020): retrieves via
  the same hybrid search, builds a numbered context block from the
  retrieved chunks, and calls the configured `LlmProvider` for an answer.
  Citations are built directly from the retrieved chunks (document id, page,
  chunk index, snippet, score) rather than parsed out of the LLM's own
  output, so every citation is independently verifiable against real
  retrieval results (FR-506) instead of trusting the model to self-report
  accurately. Added `GET /api/search?q=` and `POST /api/chat` (new
  `app/api/search.py`, registered in `main.py`), plus an internal
  `POST /api/internal/documents/{id}/reindex` (FR-507) that re-dispatches
  the existing idempotent `generate_embeddings` task on demand — safe to
  call any time since it upserts by `(document_id, chunk_index)` and drops
  stale trailing chunks from a prior run. 6 new passing tests
  (`apps/backend/tests/test_search_and_chat.py`, 50 total across the
  backend suite): ranking order with a fake embedding provider, the FR-501
  approval gate (chunks from an unapproved document never appear), the two
  HTTP endpoints end-to-end with fake LLM/embedding providers, and a 404
  when no indexed content matches. Re-exported `openapi.json`. Not done:
  n8n-level orchestration of the RAG pipeline (ADR-020 calls for n8n to own
  "query -> retrieval -> reranking -> ... -> response" as an observable
  workflow; this pass implements retrieval/business logic as backend
  services only, callable directly, with no n8n workflow in front of
  `/api/chat` yet) and a frontend search/chat UI (not listed under Phase
  5's PRD "In Scope" — only Phase 4 the PRD explicitly scopes frontend
  work, so this was treated as out of this pass's scope, not an oversight).

- Phase 2 (WS-02/WS-03) technical debt: document reprocessing. Added the
  `complete -> queued` and `failed -> queued` transitions to
  `document_repository.ALLOWED_TRANSITIONS` (previously both were terminal
  with no way back), and `POST /api/internal/documents/{id}/reprocess`
  (`apps/backend/app/api/internal.py`) which resets a `complete`/`failed`
  document to `queued` and re-dispatches the same
  `validate_file -> run_ocr -> extract_fields -> generate_embeddings` chain
  used for first-time processing -- safe because every task in that chain
  is already idempotent (upsert-by-key, re-checks current status). A
  document already `queued`/`processing` is rejected with 409 rather than
  silently double-dispatched (`update_status` treats a same-status write as
  a no-op elsewhere for idempotency, so this guard is explicit at the
  endpoint rather than relying on that). ADR-011 anticipated reprocessing
  as a benefit of page-level OCR storage; this closes that gap. 5 new
  passing tests (`apps/backend/tests/test_internal_processing.py`, 54 total
  across the backend suite): auth, 404, successful reset+redispatch, and
  the 409 guard. Re-exported `openapi.json`.

- WS-06 technical debt: fixed `make test-backend`'s stale docker-compose
  image. Rebuilding `backend`/`celery-worker` (`docker compose build`) to
  pick up this session's new code surfaced a real, previously-hidden bug:
  `test_regression_fixtures.py`'s `FIXTURES_DIR = Path(__file__).resolve()
  .parents[3] / "fixtures" / "ocr_extraction"` assumes the local-dev
  nesting (`apps/backend/tests/<file>` -> repo root 3 parents up), but the
  backend/celery-worker images build from `apps/backend` as their context
  (`docker-compose.yml`), so the repo-root `fixtures/` directory was never
  part of the image at all -- `parents[3]` doesn't even exist inside
  `/app/tests/<file>` in the container, so the test errored on import
  (`IndexError: 3`) rather than just failing to find files. This had been
  silently masked because the image was never rebuilt after the test was
  added (see the prior stale-image entry). Fixed by bind-mounting the
  repo-root `fixtures/` at `/app/fixtures` for the `backend` service
  (`docker-compose.yml`) and making `_fixtures_dir()` in the test try both
  the container layout (`apps/backend/fixtures`, i.e. `/app/fixtures` from
  the container's perspective) and the local-dev layout, using whichever
  exists. Verified against the real stack, not just in isolation: rebuilt
  both images, ran the full suite through `docker compose run --rm backend
  python -m unittest discover` (54/54 passing, matching the local `.venv`
  run), then `docker compose up -d backend celery-worker` to pick up the
  rebuilt images on the already-running dev stack and confirmed
  `GET /api/health` and `GET /api/search` respond correctly against the
  live Postgres/Redis. `make test-backend`'s docker-compose fallback path
  can now be trusted again. Also forwarded the new
  `SEARCH_KEYWORD_WEIGHT`/`SEARCH_VECTOR_WEIGHT`/`SEARCH_DEFAULT_LIMIT`/
  `CHAT_CONTEXT_CHUNKS` settings into the `backend` service's environment
  block and `.env.example` (WS-05's established practice, avoiding the
  exact "documented but not forwarded" bug WS-05 fixed previously).

- WS-01 technical debt: retired the frontend mock as the default. Found a
  real, previously-undiscovered bug while doing it: `docker-compose.yml`'s
  `frontend` service never forwarded `VITE_ENABLE_API_MOCKS` into the
  container at all, so the `.env` setting had zero effect on the actual
  dev-stack frontend -- it was unconditionally `undefined` inside the
  container, and `mocksEnabled` (`apps/frontend/src/main.tsx`) treated
  anything other than the literal string `"false"` as "mocks on", so the
  containerized frontend was always running against the mock API
  regardless of `.env`, even though WS-02/WS-03 have shipped real
  `/documents`, `/ocr`, `/extraction`, `/review`, `/chunks` endpoints since
  earlier this project. Fixed by forwarding `VITE_ENABLE_API_MOCKS` in
  `docker-compose.yml`, flipping the default to `false` in `.env`/
  `.env.example` (now opt-in for a frontend-only demo, not opt-out from a
  real backend), and inverting `main.tsx`'s check to match (`=== "true"`
  rather than `!== "false"`, so a missing/misconfigured env var fails safe
  toward the real backend instead of silently toward the mock). Verified
  `tsc -b` clean, rebuilt/recreated the `frontend` container on the live
  dev stack, and confirmed via the served dev-server module
  (`curl http://localhost:5173/src/main.tsx`) that `VITE_ENABLE_API_MOCKS`
  now actually reaches the browser as `"false"`. Exercised the real
  backend directly with `curl` (`POST /api/documents`, `GET /api/documents`)
  to confirm the endpoints the frontend now talks to work end-to-end;
  uploads currently land as `status: "failed"` /
  `"Failed to trigger processing workflow"` -- this is the pre-existing,
  already-documented n8n `Internal API Key` credential gap (WS-04 Technical
  Debt), not a regression from this change. Could not visually
  click-through in an actual browser: the Chrome extension used for
  browser automation was not connected this session (same limitation
  noted in every prior WS-01 entry) -- this change is verified at the
  network/build level, not with a real screenshot.

## In Progress

- WS-01 Frontend: review workspace UI, closing the WS-01 Phase 4 milestone
  ("Full review workspace: edit, save draft, approve, audit trail visible")
  and most of PRD-Phase-4's FR-401-408. Backend (ADR-014) has had a fully
  tested review API since WS-02, but no frontend consumed it — this was the
  single largest gap called out in Technical Debt. Added `ReviewPanel`
  (`apps/frontend/src/features/documents/ReviewPanel.tsx`), rendered below
  the extraction panel on `DocumentDetailPage` once a document is
  `complete`: starts a review seeded from the extraction result, an
  editable form (parties/dates/monetary values/key clauses/obligations)
  while `draft_review`, save-draft/submit/approve/reject(with required
  reason)/archive actions gated by the current status (mirroring
  ADR-014's `ALLOWED_TRANSITIONS`), a status chip, and an audit-history
  dialog backed by `GET .../review/history` (FR-407). A 412 version
  conflict (concurrent edit) surfaces a warning and refetches the latest
  version rather than silently overwriting it. Added the matching
  `ReviewSummary`/`ReviewRevision`/`ReviewStatus` types and
  `getReview`/`createReview`/`saveDraft`/`submitReview`/`approveReview`/
  `rejectReview`/`reviseReview`/`archiveReview`/`getReviewHistory` methods
  to `packages/api-client`, and extended the dev-only mock
  (`mockDocumentsApi.ts`) with a review store that enforces the same
  transition table as the backend, so the workspace is demoable without a
  running backend.
  Investigating "audit trail visible" surfaced a real backend gap (WS-02,
  fixed in the same pass since the frontend milestone was not fully
  achievable otherwise): ADR-014's state machine permits
  `rejected -> draft_review` (send a rejected review back for edits) but no
  endpoint exposed it — `/review/submit` always targets `in_review`, so a
  rejected review had no way back to draft through the API. Added
  `POST /api/documents/{id}/review/revise` (`apps/backend/app/api/reviews.py`,
  reusing the existing generic `_transition` helper) and extended
  `test_full_approval_lifecycle` in `test_reviews_api.py` to cover
  reject -> revise -> edit end to end. Re-exported `openapi.json`
  (`make export-openapi`) to pick up the new endpoint. Full 44-test backend
  suite still passes (`make test-backend` via the backend `.venv`).
  Verified with `tsc -b` and `vite build` (both clean). Could not verify in
  an actual browser: the Chrome extension used for browser automation was
  not connected this session (same limitation as the prior WS-01 entry) —
  the panel's rendering/state-machine behavior is confirmed by the mock's
  logic and type checks only, not a real click-through.
- WS-01 Frontend: Phase 3 extraction panel, closing the WS-01 Phase 3
  milestone ("Extraction fields rendered from structured JSON; validation
  errors surfaced"). Added a panel to `DocumentDetailPage` below the
  PDF/OCR viewer, backed by a new `ApiClient.getExtraction()` in
  `packages/api-client` (`ExtractedContractFields`/`ExtractionResult`
  types) that polls `GET /documents/{id}/extraction` until a result lands,
  rendering parties/dates/monetary values/key clauses/obligations with a
  confidence chip and the prompt/model version footer (FR-306/307/308).
  Investigating "validation errors surfaced" surfaced a real backend gap
  (WS-02/WS-03, fixed in the same pass since the frontend milestone was not
  achievable otherwise): `documents.extract_fields`
  (`apps/backend/app/tasks/extraction.py`) treated a schema-invalid LLM
  response as terminal (FR-303/304) but only logged it — nothing was
  persisted, so `GET .../extraction` returned an identical 404 "Extraction
  not found" whether extraction had never run or had run and failed
  validation, and there was no way for any client to tell those apart.
  Added `extraction_service.record_extraction_failure` (writes an
  `extraction_validation_failed` audit-log entry, ADR-015) and
  `audit_repository.get_latest`; the endpoint now returns 422 with the
  validation reason when a prior attempt failed, vs. 404 when none has run
  yet. Updated `test_ai_pipeline.py`'s validation-failure test for the new
  422. Extended the dev-only mock (`mockDocumentsApi.ts`) to generate a
  fake extraction result once a document reaches `complete`, so the panel
  is demoable without the real backend. Also fixed a pre-existing,
  unrelated OpenAPI drift: `packages/api-client/openapi.json` was missing
  WS-04's `/api/internal/documents/{id}/process` endpoint entirely (present
  on `main` before this change — `make verify-openapi`/CI would have caught
  it on the next PR touching that file regardless), re-exported via
  `make export-openapi`. Verified with `tsc -b` (clean) and the full
  44-test backend suite (`make test-backend` via the backend `.venv`;
  `make test-backend`'s own docker-compose fallback path only picks up 42 —
  its container image predates `test_ingestion_integration.py`/
  `test_regression_fixtures.py` and needs a rebuild, see Technical Debt).
  Could not verify in an actual browser: the Chrome extension used for
  browser automation was not connected this session, so the panel's
  rendering/polling behavior is confirmed by type/unit tests only, not a
  real click-through.
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
- ~~`apps/frontend/src/mocks/mockDocumentsApi.ts` is still in place, mock
  vs. real backend undecided~~ Resolved: `VITE_ENABLE_API_MOCKS` now
  defaults to `false` (real backend) and is actually forwarded into the
  `frontend` container (see Completed, below -- it previously wasn't). The
  mock module itself is kept, opt-in, for frontend-only demos.
- The `Review`/`ReviewRevision` state machine (ADR-014) was implemented
  ahead of Phase 2/3 (OCR, extraction) to satisfy WS-02's Done Criteria.
  `POST /api/documents/{id}/review` still takes a caller-supplied `content`
  payload rather than seeding itself from the document's extraction
  (`review_service.start_review`'s docstring still flags this as the
  backend's responsibility to pick up). WS-01's `ReviewPanel` now works
  around this at the call site — it seeds `createReview` with the
  extraction result when starting a review — but that's a frontend
  convention, not a backend guarantee; a caller that skips the UI can still
  start a review with arbitrary content. The review API itself (transitions,
  optimistic locking, append-only revision history, audit log) is real and
  fully tested, not a placeholder.
- WS-01's `ReviewPanel` (review workspace UI, Phase 4) has not been
  exercised in an actual browser — the Chrome extension used for browser
  automation was not connected in either this session or the one that
  built the extraction panel. Confirmed via `tsc -b`/`vite build` and the
  mock's own transition-table logic only; needs a real click-through
  (start review -> edit -> save draft -> submit -> approve/reject -> revise
  -> archive, plus the 412 conflict path) before Phase 4 can be called
  visually verified.
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
- Made a real attempt at exercising `paddleocr` inside the actual
  `celery-worker` container (this environment's Docker Desktop was
  running the full stack, unlike prior sessions) and got further than
  before, but it's still not working end-to-end:
  1. Uploaded `fixtures/ocr_extraction/sample_contract.pdf` via
     `POST /api/documents` and drove it through the real pipeline with the
     new `POST /api/internal/documents/{id}/reprocess` (bypassing the
     n8n-credential blocker below entirely). It failed immediately with
     `OCR_ENGINE=paddleocr but the paddleocr package is not installed` --
     misleading, since `paddleocr` *is* installed; `import paddleocr`
     actually fails deep in `paddlepaddle`'s own import chain
     (`paddle.utils.cpp_extension` -> `import setuptools` ->
     `ModuleNotFoundError`) because paddlepaddle uses `setuptools` at
     runtime without declaring it as a dependency, and the `python:3.12-slim`
     base image no longer bundles it. Fixed for real: pinned
     `setuptools==75.1.0` in `apps/backend/requirements.txt`, rebuilt, and
     confirmed `import paddleocr` gets past that error.
  2. With that fixed, `import paddle` **segfaults** (exit 139) on this
     machine -- confirmed directly with
     `docker compose exec celery-worker python -c "import paddle"`. This
     environment is Docker Desktop on Apple Silicon (`uname -m` ->
     `aarch64`); `paddlepaddle==2.6.2`'s behavior on aarch64 Linux is the
     suspect, not a Python-level fix. This is a genuinely different, harder
     problem than "not installed" (a native crash in a pinned third-party
     ML wheel) and trying paddlepaddle version/build alternatives blindly
     risked leaving the pinned dependency in a worse, unverified state than
     documenting the precise failure -- deliberately stopped here rather
     than guess further. The `setuptools` fix stands regardless (it's a
     real bug independent of the segfault, and likely unblocks paddleocr
     entirely on an x86_64 host). Next step for whoever picks this up:
     reproduce on x86_64, or try a newer `paddlepaddle` release with
     official aarch64 wheels.
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
- ~~The document status state machine had no transition back out of
  `complete`/`failed`~~ Resolved: `complete`/`failed -> queued` is now
  allowed and `POST /api/internal/documents/{id}/reprocess` resets and
  re-dispatches the pipeline (see Completed, below). The n8n watchdog
  (`n8n/workflows/02-processing-watchdog.json`) still only surfaces stuck
  documents rather than calling this endpoint automatically -- wiring an
  actual auto-retry policy (vs. an operator-triggered one) is still
  unstarted and deserves its own decision on retry limits/backoff.

- ~~The `backend` image `make test-backend`'s docker-compose fallback path
  runs against is stale~~ Resolved: rebuilt (`docker compose build backend
  celery-worker`) and verified 54/54 tests pass through
  `docker compose run --rm backend python -m unittest discover` (see
  Completed, below). Rebuilding surfaced and fixed a real bug in
  `test_regression_fixtures.py`'s fixtures-directory path resolution that
  the stale image had been hiding. CI (`.github/workflows/backend.yml`)
  builds a fresh image every run, so it was never affected by this --
  only the local `make test-backend` fallback was stale.
- `apps/frontend/node_modules` was missing the platform-specific
  `@rollup/rollup-darwin-arm64` optional dependency (a known npm bug,
  npm/cli#4828), breaking both `vite build` and `vite --host ...` (dev
  server) with a native-module error unrelated to any source change. Fixed
  with a plain `npm install` (no lockfile/package.json changes needed) —
  if this recurs, that's the fix; no need to delete `node_modules`/
  `package-lock.json` as the error message itself suggests.

- Phase 5's Search/Chat APIs (`app/services/search_service.py`,
  `app/services/rag_service.py`) are backend-only: ADR-020 specifies n8n
  should orchestrate the RAG pipeline (query -> retrieval -> reranking ->
  prompt -> LLM -> citations -> response) for observability, but no
  `n8n/workflows/` entry fronts `/api/chat` yet -- it's called directly.
  There's also no frontend for search/chat (not in Phase 5's PRD scope, so
  this is expected, not a gap against PRD-5's Acceptance Criteria, but
  users can only reach these APIs via `curl`/Swagger today). Hybrid
  ranking is a fixed formula (`SEARCH_KEYWORD_WEIGHT`/`SEARCH_VECTOR_WEIGHT`
  applied uniformly); ADR-019's "configurable ranking" is satisfied at the
  weight level, not with pluggable ranking strategies. Vector similarity is
  computed in Python over every approved chunk's JSON-stored embedding
  (`search_service._cosine_similarity`, O(n) per query) rather than an ANN
  index query -- fine at fixture scale, but depends on the pgvector-column
  migration below to scale.

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

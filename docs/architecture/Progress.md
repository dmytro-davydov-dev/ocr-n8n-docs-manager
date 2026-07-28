# Progress

_Last updated:_ 2026-07-28 (Full saga: documents wedged in `processing` forever, traced through four stacked causes down to a confirmed upstream PaddleOCR/PaddlePaddle native memory leak; added Tesseract as a working alternative engine. See below and ADR-010's addendum.)

## Overall Status

- **Current Phase:** Phase 5 – Search & RAG
- **Overall Progress:** 68%
- **Project Status:** 🟢 On Track

---

# Phase Tracker

| Phase | Status | Progress | PRD | ADRs |
|---|---|---:|---|---|
| Phase 0 – Foundation | ✅ | 100% | [[templates/PRD-Phase-0-Foundation\|PRD-0]] | ADR-001 to ADR-009 |
| Phase 1 – Document Ingestion | 🔶 | 85% | [[templates/PRD-Phase-1-Document-Ingestion\|PRD-1]] | — |
| Phase 2 – OCR Pipeline | 🔶 | 95% | [[templates/PRD-Phase-2-OCR-Pipeline\|PRD-2]] | ADR-010, ADR-011 |
| Phase 3 – AI Extraction | 🔶 | 80% | [[templates/PRD-Phase-3-AI-Extraction\|PRD-3]] | ADR-012, ADR-013 |
| Phase 4 – Contract Review UI | 🔶 | 65% | [[templates/PRD-Phase-4-Contract-Review-UI\|PRD-4]] | ADR-014, ADR-015 |
| Phase 5 – Search & RAG | 🔶 | 85% | [[templates/PRD-Phase-5-Search-and-Knowledge-Base-RAG\|PRD-5]] | ADR-016 to ADR-020 |

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

- Documentation: filled in the seven previously-empty "Technical Areas" pages
  linked from `docs/MOC.md` (`docs/frontend/README.md`, `docs/backend/README.md`,
  `docs/docker/README.md`, `docs/database/README.md`, `docs/security/README.md`,
  `docs/testing/Test-Strategy.md`, `docs/observability/README.md`) — all had
  existed as empty files/broken wiki-links. Content was written from direct
  inspection of the actual source (models, routers, `docker-compose.yml`,
  `Dockerfile`s, `Makefile`, migrations, test files), not guessed, per this
  file's own standing instruction. `observability/README.md` and
  `security/README.md` in particular document real, current gaps (no metrics/
  tracing/log aggregation; no end-user auth) rather than aspirational content.

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

- Phase 3/5 live verification: exercised the real `OpenAiCompatibleLlmProvider`/
  `OpenAiCompatibleEmbeddingProvider` HTTP code paths and the new Phase 5
  Search/Chat APIs end-to-end against the live docker stack, using a
  throwaway local stub standing in for an OpenAI-compatible endpoint (no
  real LLM/embedding account available in this environment). Confirmed
  `extract_fields`/`generate_embeddings` correctly call, parse, and persist
  real HTTP responses (not just fakes), and that an approved review's
  chunks are correctly retrievable via `GET /api/search` and
  `POST /api/chat` with accurate citations. See Technical Debt for what
  this does and doesn't cover, and how the environment was reverted
  afterward.

- Phase 5 (WS-04/ADR-020): added `n8n/workflows/03-rag-chat.json`, an n8n
  workflow fronting `POST /api/chat` as an observable pipeline step
  (query -> n8n webhook -> backend retrieval/LLM/citations -> response),
  per ADR-020's "n8n orchestrates, backend owns retrieval and business
  logic". Unlike `01`/`02`, it calls a public backend endpoint, so it needs
  no `Internal API Key` credential to be useful. Validated with the same
  bar as prior workflow exports -- actually imported into the live n8n
  instance (`docker compose exec n8n n8n import:workflow --separate
  --input=/workflows`), not just JSON-parsed; it imported successfully
  alongside the existing three. Also corrected two stale claims in
  `n8n/workflows/README.md` found while doing this: it said the `n8n`
  service doesn't mount `./n8n/workflows` (it does --
  `./n8n/workflows:/workflows:ro`, and the import runs automatically on
  every container start per the compose `command:`, not as a manual step),
  and it attributed auto-deactivation-on-import specifically to missing
  credentials (confirmed directly: the CLI deactivates every imported
  workflow regardless). Like `01`/`02`, `03` lands inactive after import
  and needs a one-time manual reactivation in the n8n UI -- confirmed by
  hitting the webhook post-import and getting n8n's own "workflow must be
  active" 404, not a crash or malformed-workflow error.

- Phase 4: found and fixed two real bugs in `ReviewPanel.tsx`
  (`apps/frontend/src/features/documents/ReviewPanel.tsx`) by tracing the
  code against `packages/api-client`'s actual contract, since the Chrome
  extension wasn't available to find them by clicking through. (1)
  `api.getReview` returns `null` specifically on 404 (no review yet) and
  throws `ApiError` for any other failure (`packages/api-client/src/
  index.ts`), but the panel never checked `reviewQuery.isError` -- a real
  fetch failure (500, network error) would silently render "No review has
  been started for this document yet" with a "Start review" button, same
  as the expected no-review-yet case, hiding the actual error and inviting
  the user to create a duplicate review. Now shows an explicit error Alert
  and suppresses the "Start review" prompt when the query itself failed.
  (2) React Query leaves a mutation's `isError` set until it's retried or
  reset; `pendingMutation` picked the first mutation (of 7) matching
  `isPending || isError` in a fixed array order, so once e.g. a save-draft
  failed once, that stale error banner would keep shadowing every later,
  unrelated, even successful action (submit, approve, ...) for the rest of
  the session -- there was no way to dismiss it short of navigating away.
  Added `runMutation()`, which resets every sibling mutation before firing
  the one the user just triggered, and routed all 9 button handlers through
  it. Verified with `tsc -b` and `vite build` (both clean); still could not
  click-through in an actual browser (Chrome extension not connected this
  session either — confirmed via `tabs_context_mcp`).

- Phase 4: fixed a real bug in `DocumentDetailPage.tsx`'s status polling,
  found the same way as the `ReviewPanel` fixes -- tracing the code against
  `document_repository.ALLOWED_TRANSITIONS` (`complete`/`failed` are both
  terminal from the viewer's perspective) rather than clicking through a
  browser. `documentQuery`'s `refetchInterval` only stopped on `"complete"`,
  so a `failed` document (the common case before the n8n credential is set
  up, see Technical Debt) polled `GET /api/documents/{id}` every 2 seconds
  forever with no way to stop short of navigating away. Also, a `failed`
  document previously rendered the same generic info alert as an
  in-progress one ("OCR is still failed" — confusing wording, wrong
  severity, and `DocumentSummary.errorMessage` was fetched but never
  displayed). Now stops polling on `failed` too and shows a proper error
  alert with the actual `errorMessage`. Verified with `tsc -b` and
  `vite build` (both clean).

- Phase 2: got real `paddleocr` OCR working end-to-end in the actual
  `celery-worker` container for the first time (previously verified only
  via `compileall`). Found and fixed three stacked bugs blocking it
  (missing `setuptools`, a `paddlepaddle==2.6.2` segfault on this host's
  aarch64 architecture, a missing `libgl1` system library for `cv2`) and
  confirmed real OCR output (~99% confidence, correct text) both by
  calling `PaddleOcrEngine` directly and by driving a real upload through
  the actual pipeline via `/reprocess` with `OCR_ENGINE=paddleocr`. See
  Technical Debt for the full blow-by-blow.

- n8n upload workflow needed a one-time manual credential setup: scripted the
  previously-manual n8n bootstrap. Added
  `infra/n8n-credentials.template.json` (committed, placeholder value only —
  `__INTERNAL_API_KEY__`) and `infra/n8n-bootstrap.sh`, which the `n8n`
  service now runs on every container start in place of a bare
  `n8n import:workflow`: it `sed`s the container's own `INTERNAL_API_KEY` env
  var into the template, `n8n import:credentials`s it (creating the `Internal
  API Key` HTTP Header Auth credential the exported workflows reference by id
  `internal-api-key`), deletes the rendered file, imports the workflows, then
  explicitly reactivates `01`/`02`/`03` with
  `n8n update:workflow --active=true --id=<id>` (n8n's CLI importer
  deactivates every workflow it imports regardless of credentials, confirmed
  in a prior session's own log output — reactivation was always going to be
  needed either way). A fresh `docker compose up` should no longer need any
  hand-created credential or manual reactivation in the n8n UI. Updated
  `n8n/workflows/README.md` and the docker-compose `n8n` service
  (`INTERNAL_API_KEY` env + two new read-only volume mounts) to match.
  **Not verified against a live n8n instance this session** (no docker
  available in this environment, unlike prior WS-04 sessions that actually
  imported into a running n8n 1.71.3) — validated at the level this session
  could reach: the credentials/workflow JSON parse, the shell script passes
  `sh -n`, and the compose file's structure was checked with `pyyaml`. Next
  person to run `docker compose up --build` should confirm the `Internal API
  Key` credential exists and `01`/`02`/`03` are active without touching the
  n8n UI, then check off the matching item under Verification Follow-ups.

- No automated recovery for stuck/failed documents: added a
  bounded auto-retry policy instead of the watchdog only surfacing failures.
  `Document.retry_count` (migration `0009_documents_retry_count`, backfilled
  0) tracks how many times a document has been auto-retried. New
  `POST /api/internal/documents/{id}/auto-retry`
  (`apps/backend/app/api/internal.py`): only acts on `failed` documents,
  rejects with 409 once `retry_count >= DOCUMENT_AUTO_RETRY_MAX` (new config,
  default 3, forwarded into the `backend` service's environment/`.env.example`/
  README table), otherwise increments `retry_count` (audit-logged as
  `auto_retry`), resets the document to `queued`, and re-dispatches the same
  idempotent pipeline chain `/reprocess` uses. `/reprocess` (the existing
  operator-triggered path) now resets `retry_count` back to 0 first — a
  deliberate manual reprocess is a fresh attempt, not a continuation of the
  auto-retry budget. Exposed `retryCount` on `DocumentSummary`
  (backend schema, regenerated `packages/api-client/openapi.json` via
  `make export-openapi`, `verify-openapi` confirms no drift, and the
  hand-kept `packages/api-client/src/index.ts` type + `mockDocumentsApi.ts`'s
  document literal). Rewrote `n8n/workflows/02-processing-watchdog.json`: it
  still lists `GET /api/documents` and still only *logs* documents stuck in
  `queued`/`processing` >15 min (re-dispatching wouldn't fix a wedged
  worker/broker), but `failed` documents now branch through a new `Is Failed`
  node into an `Auto Retry` HTTP node calling `.../auto-retry`
  (`neverError`+`fullResponse` so a 409 lands as data, not a failed n8n
  execution) and a `Log Auto Retry Outcome` code node. 6 new backend tests
  (`apps/backend/tests/test_internal_processing.py`, 63 total across the
  suite, all passing via `python3 -m unittest discover` against SQLite —
  installed the backend's non-paddleocr dependencies directly into this
  session's Python to run them, no docker needed for this part) cover the
  retry-count reset, the new endpoint's auth/404/409-wrong-status/dispatch
  paths, and that the budget is actually enforced (409 with "exhausted" once
  `DOCUMENT_AUTO_RETRY_MAX` auto-retries have been used). Also ran `tsc -b`
  clean on the frontend after the `api-client` type change.
  **Not verified against a live n8n instance** (same no-docker caveat as the
  n8n bootstrap entry above): the workflow JSON parses and its node graph is
  internally consistent, but it has not been imported into a real n8n and
  fired against a real `failed` document. Next person with the stack running
  should trigger a real failure, let the watchdog's 10-minute schedule (or a
  manual execution) fire, and confirm `retry_count` increments and the
  document reaches `queued` again (see Verification Follow-ups).

- paddleocr's real output doesn't match the checked-in golden fixture: added
  `apps/backend/scripts/refresh_ocr_fixture.py` and
  `make refresh-ocr-fixture`, which rasterizes `fixtures/ocr_extraction/
  sample_contract.pdf` the same way `app/tasks/ocr.py` does and runs it
  through the real `PaddleOcrEngine` (not the fake engine
  `test_regression_fixtures.py` uses), writing real output to
  `sample_contract.ocr.json`. This only prepares the tooling — **it has not
  been run**, since real paddleocr/paddlepaddle need native dependencies
  (and previously needed three stacked fixes for this project's aarch64 host,
  see Technical Debt below) that aren't available in this session's
  environment. Someone with the stack running needs to run
  `make refresh-ocr-fixture` and review/commit the resulting diff — still the
  lowest-priority open item, this doesn't affect the test suite either way.

- Documentation: filled in `docs/vision/Vision.md` and `docs/vision/Goals.md`
  (previously empty, broken wiki-links from `docs/MOC.md`). Content was
  written from the actual PRDs, ADRs, `docs/workstreams/README.md`, and this
  file, not invented — Vision covers the problem statement, target users,
  the upload → OCR → AI extraction → review → search/RAG pipeline, and
  guiding principles (human-in-the-loop, provider independence,
  contract-first parallelism); Goals covers the north-star goal, a per-phase
  goals table sourced from each PRD's own Goals/Exit Criteria, and
  cross-cutting engineering goals. Also added `docs/Tech-Glossary.md`, a
  plain-language reference (OCR, CV, ML, LLM, RAG, embeddings, chunking,
  vector database, etc., plus the project's own tools and document types)
  for non-technical readers, linked from a new "Reference" section in
  `docs/MOC.md` and from the "Knowledge Base" section of the root
  `README.md`.

- Documentation: converted `docs/Tech-Glossary.md`'s entries from a table
  into one heading per term (`### OCR`, `### AI`, etc.) so each definition
  has a stable anchor, then linked every first occurrence of a glossary term
  in the four high-level docs (`README.md`, `docs/MOC.md`,
  `docs/vision/Vision.md`, `docs/vision/Goals.md`) to its glossary entry —
  Obsidian `[[Tech-Glossary#Term|term]]` links in the wiki-linked docs,
  standard `[term](docs/Tech-Glossary.md#anchor)` links in `README.md` to
  keep it renderable on GitHub. Deliberately skipped occurrences inside code
  spans/fenced blocks (e.g. `` `pgvector` ``, the ASCII architecture diagram)
  and inside text that was already part of another link's label, and only
  linked the first occurrence of each term per document rather than every
  repetition, to avoid link spam in the environment-variable table and
  elsewhere.

- Bugfix: documents stuck in `processing` forever (reported via a UI
  screenshot showing a document go `failed` -> `processing` and never
  resolve). Root cause was two stacked gaps in `apps/backend/app/tasks/`,
  both named as risks in ADR-008 but never actually closed: (1) every task's
  `raise self.retry(exc=exc)` call, once `max_retries` is exhausted, makes
  Celery raise `MaxRetriesExceededError` instead of retrying — none of the
  four tasks caught it, so the exception just killed the task without ever
  persisting a terminal `failed` status, leaving the document's row wedged
  at whatever status it was last written to (usually `processing`, set by
  `validate_file` right before `run_ocr` hit the exhausted-retry path); (2)
  no task had a Celery `time_limit`/`soft_time_limit` configured at all, so
  a genuinely hung call (e.g. an OCR engine call that never returns and
  never raises) produced no exception for anything to catch, meaning even
  the fix for (1) couldn't help. The watchdog (`02-processing-watchdog.json`)
  deliberately never auto-heals `queued`/`processing` — by design, a wedged
  worker isn't fixed by re-dispatching the same chain — so there was no
  automated recovery path once a document landed here.
  Fixed both: `validate_file`/`run_ocr`/`extract_fields`/`generate_embeddings`
  now catch `MaxRetriesExceededError` at every `self.retry()` call site and
  persist a terminal outcome (`failed` for `validate_file`/`run_ocr`, which
  run while `document.status == 'processing'`; an audit-trail-only failure
  via `extraction_service.record_extraction_failure`/new
  `embedding_service.record_failure` for `extract_fields`/
  `generate_embeddings`, which run while `document.status == 'complete'` and
  have no `complete -> failed` edge in `ALLOWED_TRANSITIONS` by design — see
  existing `validation_failed` handling for the same reason). Added
  `soft_time_limit`/`time_limit` to all four tasks (new
  `*_SOFT_TIME_LIMIT_SECONDS`/`*_TIME_LIMIT_SECONDS` settings, forwardable
  via env) and a `SoftTimeLimitExceeded` handler in each with the same
  terminal-outcome split as above.
  Even with both fixed going forward, a document already wedged from before
  this fix (or one that gets wedged for an unrelated infra reason later) had
  no supported way out: `/reprocess` only accepted `complete`/`failed`, and
  a document stuck in `queued`/`processing` isn't either. Added
  `processing -> queued` to `ALLOWED_TRANSITIONS` and extended
  `POST /api/internal/documents/{id}/reprocess` to accept `queued`/
  `processing` too, but only once the document has been sitting there
  longer than the watchdog's own stuck-detection window (new
  `DOCUMENT_STUCK_THRESHOLD_MINUTES` setting, default 15, deliberately
  mirroring `02-processing-watchdog.json`'s hardcoded `STALE_THRESHOLD_MS`)
  — a document still genuinely mid-pipeline within that window is rejected
  with 409, same as before, so this can't double-dispatch a real in-flight
  run.
  Exposed this to the frontend: added
  `POST /api/documents/{id}/reprocess` (`apps/backend/app/api/documents.py`,
  same rules as the internal endpoint, reusing its `_dispatch_pipeline`/
  `_minutes_since_update` helpers) since the browser shouldn't hold
  `INTERNAL_API_KEY`, added `ApiClient.reprocessDocument` to
  `packages/api-client`, and added a "Reprocess" button next to
  Archive/Unarchive in `DocumentList.tsx` for any non-archived document.
  7 new/updated backend tests (`test_internal_processing.py`, 79 total
  across the suite — installed the backend's non-paddleocr deps directly
  into this session's Python to run the full suite, no docker available)
  cover the exhausted-retry-vs-terminal-failure split is unaffected, the new
  `processing -> queued` staleness gate (both the 409-while-fresh and the
  succeeds-once-stale paths), and retry-count reset. Verified `tsc -b`
  clean on the frontend after the `api-client`/`DocumentList.tsx` changes.
  **Not verified against a live stack** (no docker in this session) — the
  reported document was already wedged before this fix landed and needs a
  manual `/reprocess` (now clearable via the new staleness override, or the
  UI button) once the rebuilt `celery-worker` image is running; a genuinely
  new upload hitting a transient OCR/LLM/embedding failure repeatedly should
  now surface as `failed` (or an audit-logged extraction/embedding failure)
  within its task's time limit instead of hanging, but this hasn't been
  exercised against real paddleocr/LLM/embedding providers this session.

- Bugfix follow-up: the `processing`-stuck-forever fix above (task-level
  `MaxRetriesExceededError`/`SoftTimeLimitExceeded` handling) turned out not
  to be the whole story. Reprocessing the reported document with the fix
  deployed still got stuck in `processing` again; `docker compose logs
  celery-worker` showed why: `Process 'ForkPoolWorker-1' pid:8 exited with
  'signal 9 (SIGKILL)'` / `WorkerLostError('Worker exited prematurely:
  signal 9 (SIGKILL)')` during `run_ocr`, right after `PaddleOcrEngine`
  downloaded its det/rec/cls models (paddleocr's lazy first-use
  initialization, `app/services/ocr_engine.py`) — almost certainly the OOM
  killer (or the `WORKER_MEMORY_LIMIT` cgroup limit, default 4G) killing the
  worker child mid-model-load/inference. SIGKILL can't be caught in Python,
  so no amount of task-level `try`/`except` (the fix above included) can
  ever run for this — the process is gone before any of that code executes.
  Worse, `celery_app.py` never configured `task_acks_late`, so Celery's
  default (ack on receipt, before execution) meant the task message was
  already gone from the broker by the time the child was killed: nothing
  ever re-attempted it, so the document was stranded with zero further
  activity, indistinguishable from a hang from the API's perspective.
  Fixed the part that's actually fixable in code: added
  `task_acks_late=True` + `task_reject_on_worker_lost=True` +
  `worker_prefetch_multiplier=1` to `celery_app.py`, so a worker killed
  mid-task now gets its message requeued for another attempt instead of
  silently dropped — safe since every pipeline task already re-checks the
  document's current status before acting (ADR-008/009 idempotency).
  Also added a `paddleocr_cache` volume for `celery-worker` at
  `/root/.paddleocr` (`docker-compose.yml`) — without it, every container
  recreate (including the ones this exact crash triggers) throws away the
  downloaded models and forces a full re-download on the next OCR task,
  adding avoidable time/network/memory pressure on top of whatever caused
  the crash. The underlying memory pressure itself is a host/infra decision,
  not something this session could fix: whoever runs the stack next should
  raise `WORKER_MEMORY_LIMIT` (`.env`, default 4G) and confirm Docker
  Desktop's own VM memory allocation has headroom above that, or set
  `OCR_ENGINE=null` temporarily to validate the rest of the pipeline
  (extraction, embeddings, review) independent of paddleocr's footprint.
  Full 72-test backend suite still passes after the `celery_app.py` change;
  `docker-compose.yml` validated with `pyyaml`. **Not verified against a
  live worker actually surviving a real OOM this session** (no docker
  available) — next person should reproduce the SIGKILL, confirm the task
  gets redelivered (celery-worker logs should show the same task id picked
  up again rather than the document just sitting there), and confirm
  whether raising `WORKER_MEMORY_LIMIT` actually lets `run_ocr` complete.

- Bugfix follow-up #3: isolated the OOM to page *count* within a single
  `run_ocr` call, not a corrupt/oversized page or the JIT-compile loop
  (previous two entries). Two live checks with the user, no code changes
  needed to run them: (1) reprocessing `fixtures/ocr_extraction/
  sample_contract.pdf` (2 pages) completed fine under the exact same image;
  the real signed contract (6 pages) still got stuck in `processing` every
  time. (2) a PyMuPDF one-liner run inside the container confirmed the
  signed contract's pages are unremarkable -- standard A4 (595x842pt),
  ~11.6MB raw RGB per rendered page at the configured 200 DPI, nothing
  pathological. Since `requirements.txt`/`app/services/ocr_engine.py` are
  byte-for-byte identical to commit `9384742` ("verify real OCR works" --
  checked via `git diff`, see the "18 commits back" discussion below), the
  only variable left is that `run_ocr` calls `active_engine.recognize_page()`
  in a loop across all of a document's pages, reusing one long-lived
  `PaddleOCR` instance, with nothing releasing memory between iterations --
  consistent with the steady climb (not a sudden spike) `docker stats`
  showed earlier: 2 pages stays under the limit, 6 doesn't.
  Added an explicit `del pixmap, image_bytes, result` + `gc.collect()` at
  the end of each page iteration in `app/tasks/ocr.py`'s loop, targeting
  the hypothesis that PaddlePaddle's CPU allocator isn't returning memory to
  the OS between inference calls within the same process. Full 72-test
  backend suite still passes. **Not yet verified against the real signed
  contract** -- next step is rebuild `celery-worker`, reprocess it again,
  and watch `docker stats` for a flat/bounded profile across all 6 pages
  instead of a climb. If it still OOMs, the leak is likely inside
  paddlepaddle's own C++ runtime (below what `gc.collect()` can reach) and
  the more reliable fix would be running each page's OCR call in a fresh
  subprocess rather than in-process, or switching this environment to
  `OCR_ENGINE=null`/a lighter engine.
- Aside: considered checking out `HEAD~18` to compare against a "previously
  working" state per the user's request, but the commit log shows `HEAD~18`
  (`0d4c5d4`) predates both of this project's paddleocr-on-ARM64 fixes
  (`b2057c5` missing-setuptools fix, 12 commits back; `9384742` segfault fix
  + "verify real OCR works", 4 commits back) -- going back that far would
  almost certainly land somewhere paddleocr doesn't even import, not a
  meaningful comparison point. Declined the checkout in favor of the two
  live checks above, which don't require a rebuild-per-attempt bisection
  cycle and (per `git diff 9384742 HEAD`) would have compared identical OCR
  code anyway.

- Bugfix follow-up #4 (resolution): confirmed the page-count-dependent OOM
  (previous entry) is a known, upstream, unfixed PaddleOCR/PaddlePaddle bug
  via web search -- multiple open GitHub issues describe exactly this
  pattern (CPU inference RSS climbing across sequential calls within one
  process, never released), independent of this project's version pins:
  [#15631](https://github.com/PaddlePaddle/PaddleOCR/issues/15631),
  [#17955](https://github.com/PaddlePaddle/PaddleOCR/issues/17955),
  [#16173](https://github.com/PaddlePaddle/PaddleOCR/issues/16173). One
  thread traces it to an internal runtime program-cache keyed per distinct
  image rather than anything tied to the Python `PaddleOCR` object's
  lifetime -- consistent with `gc.collect()` (previous entry) not touching
  it.
  Decision (full reasoning in ADR-010's addendum, `docs/architecture/
  templates/ADR-010-OCR-Engine-Selection.md`): rather than subprocess-
  isolating each PaddleOCR page call (real fix, but real engineering effort
  and per-page latency, for a dependency that's now cost this project three
  separate platform-specific failures -- the ARM64 segfault, the missing-
  setuptools import failure, and this leak), added **Tesseract** as a
  second, fully-supported engine and switched this environment to it.
  Added `TesseractOcrEngine` (`app/services/ocr_engine.py`, wired into the
  existing `_ENGINES`/`get_ocr_engine()` config-driven selection alongside
  `PaddleOcrEngine`/`NullOcrEngine` -- ADR-010's "swappable via
  configuration, not code changes" requirement doing its job), a new
  `OCR_TESSERACT_LANG` setting (default `eng`; tesseract uses 3-letter ISO
  639-2 codes, a different convention than PaddleOCR's 2-letter codes, so
  it's its own setting), `pytesseract` + unpinned `pillow` in
  `requirements.txt`, and `tesseract-ocr`/`tesseract-ocr-eng`/
  `tesseract-ocr-por` in the Dockerfile (this project's real test documents
  are Portuguese-language contracts). Set `OCR_ENGINE=null` in `.env`
  immediately as an unblock (extraction/embeddings/review work without
  waiting on OCR), pending the user rebuilding and switching to
  `OCR_ENGINE=tesseract` once verified in their environment.
  Verified for real, not just reasoned about -- `tesseract` happened to
  already be installed in this session's own dev shell, so
  `TesseractOcrEngine` was exercised directly: correctly recognized real
  rendered text, reported a real engine version (4.1.1), and **30 repeated
  `recognize_page` calls against the same image showed zero RSS growth**
  (flat at ~87MB), unlike PaddleOCR's multi-GB climb on a real 6-page
  document. Added `apps/backend/tests/test_ocr_engine.py` (8 new tests:
  real recognition + line-structure + the repeated-calls-don't-grow-memory
  regression test + `OcrEngineUnavailable` on missing
  pytesseract/tesseract-binary + `get_ocr_engine()` wiring/language
  selection). Full suite: 80 passing.
  **Not yet verified inside the actual `celery-worker` Docker image** (no
  docker in this session) -- next step for the user is rebuilding with
  `docker compose up --build -d celery-worker` (picks up the new
  `tesseract-ocr` apt packages), setting `OCR_ENGINE=tesseract` in `.env`,
  and reprocessing the real signed contract to confirm both real OCR output
  and flat memory in `docker stats`, same as this session's local
  verification.

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

Only items that need a human's own hands (a real browser, a real API key, a
machine with real paddleocr) are listed here. The n8n manual-credential-setup
and no-automated-recovery blockers that used to be #1 and #4 are resolved and
code-complete — see Completed and Technical Debt, above — and are no longer
listed as blockers; only their live confirmation (run `docker compose up`
once and watch it happen) is still open, tracked as a `[ ]` under
Verification Follow-ups below.

1. **The review workspace UI (WS-01 Phase 4 `ReviewPanel`) has never been
   click-tested in an actual browser.** It's the primary reviewer-facing
   surface of the MVP (the "Review" in Contract Review MVP), and every prior
   session lacked a connected Chrome extension — verification has been
   `tsc -b`/`vite build` and the dev mock's transition logic only. Real
   rendering/state-machine bugs (start review → edit → save draft → submit →
   approve/reject → revise → archive, plus the 412 conflict path) could exist
   undetected. Needs `docker compose up` running plus a connected Chrome
   extension to click through the full lifecycle against
   `http://localhost:5173`.
2. **LLM/embedding output quality is unverified against a real provider.**
   `OpenAiCompatibleLlmProvider`/`OpenAiCompatibleEmbeddingProvider` have only
   been exercised against a throwaway local stub that confirms HTTP
   transport/parsing correctness, never a real OpenAI/Ollama account —
   extraction accuracy and embedding semantic relevance (the actual AI value
   proposition of the MVP) are unknown. Needs a real `LLM_API_KEY`/
   `EMBEDDING_API_KEY` (OpenAI, Azure OpenAI, or a local Ollama with no key
   needed), `docker compose up`, and a human (or an LLM-as-judge pass,
   deliberately not built) to judge whether extracted fields/chat answers are
   actually accurate on a real contract — not something a transport-level
   test can substitute for.
3. **paddleocr's real output doesn't match the checked-in golden fixture
   byte-for-byte** (`fixtures/ocr_extraction/sample_contract.ocr.json`, e.g. a
   digit/letter OCR artifact). Doesn't affect the test suite (which
   intentionally tests against a fake engine), but means the fixture isn't a
   real accuracy baseline — lowest priority of the open items. Run
   `make refresh-ocr-fixture` on a machine with the real paddleocr/
   paddlepaddle native deps (the `celery-worker` image already has them) and
   review/commit the diff.

## Verification Follow-ups

Code-complete, not yet confirmed against a live stack (no docker in the
session that built them) — quick checks for whoever next runs
`docker compose up`, not blockers:

- [ ] Fresh `docker compose up --build` creates the `Internal API Key` n8n
      credential and activates `01`/`02`/`03` without touching the n8n UI;
      an upload no longer lands in `status: "failed"` /
      `"Failed to trigger processing workflow"` out of the box
      (`infra/n8n-bootstrap.sh`).
- [ ] A real `failed` document gets auto-retried by
      `02-processing-watchdog.json` (`retry_count` increments, document
      returns to `queued`), and stops with a 409 once
      `DOCUMENT_AUTO_RETRY_MAX` is reached.
- [ ] After rebuilding `celery-worker` with the `processing`-stuck-forever
      fix (see Completed), confirm a real OCR/LLM/embedding transient
      failure that exhausts its retries actually lands as `failed` (or an
      audit-logged extraction/embedding failure) rather than hanging, and
      that a document already wedged from before the fix can be cleared via
      `POST .../reprocess` (internal or the new public/UI path) once past
      `DOCUMENT_STUCK_THRESHOLD_MINUTES`.

## Risks

- Docker VM disk growth may reintroduce local storage pressure over time if not periodically pruned.

## Technical Debt

- ~~WS-04's upload workflow (`n8n/workflows/01-document-upload-ingestion.json`)
  now exists and is exported `active: true`, but n8n auto-deactivates any
  imported workflow whose referenced credential doesn't exist yet -- so on
  a fresh instance (including a freshly `docker compose up`'d one) it
  imports inactive until an operator manually creates the `Internal API
  Key` HTTP Header Auth credential in the n8n UI and reactivates it~~
  Resolved: `infra/n8n-bootstrap.sh` creates the credential from the
  container's own `INTERNAL_API_KEY` and reactivates `01`/`02`/`03` on every
  `n8n` container start, so this is no longer a manual step (see
  `n8n/workflows/README.md`). Not yet confirmed against a live n8n instance
  this session (no docker available) — see Verification Follow-ups.
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
  workflow, which needed the `Internal API Key` credential created by hand
  first -- as of this session that credential is created automatically by
  `infra/n8n-bootstrap.sh` (see the resolved bullet above), but kept here
  until someone confirms live with a real `docker compose up`
  that a document reaches `processing`/`complete` through the real n8n
  webhook, not just a manual `curl` calling `/process` directly.
- ~~`paddleocr` has never been exercised in the actual `celery-worker`
  container~~ Fully resolved, closing the single longest-standing Phase 2
  gap. Three real, distinct bugs stacked on top of each other, each found
  and fixed by actually running it against the live stack rather than
  guessing:
  1. `import paddleocr` failed with a misleading `"the paddleocr package
     is not installed"` — paddlepaddle uses `setuptools` at runtime
     without declaring it as a dependency, and `python:3.12-slim` no
     longer bundles it. Fixed: pinned `setuptools==75.1.0`.
  2. With that fixed, `import paddle` **segfaulted** (exit 139) —
     confirmed directly on this machine's architecture (Docker Desktop on
     Apple Silicon, `aarch64`). `paddlepaddle==2.6.2` is the culprit, not
     a Python-level issue. Fixed by actually testing alternatives instead
     of stopping at "diagnosed": `pip index versions paddlepaddle` inside
     the container showed a 3.x line (latest 3.2.2); installed it ad hoc
     first to confirm `import paddle` succeeds before touching
     `requirements.txt`, then bumped the pin for real.
  3. With paddle importable, `import paddleocr` hit a *third*, unrelated
     issue: `ImportError: libGL.so.1: cannot open shared object file` —
     `cv2` (pulled in by paddleocr) needs a system OpenGL library the
     `python:3.12-slim` image doesn't have. Fixed: added `libgl1`/
     `libglib2.0-0` to `apps/backend/Dockerfile`'s `apt-get install`.
  With all three fixed, verified as deep as this pipeline goes, not just
  "engine constructs without crashing": rebuilt the images, instantiated
  the real `PaddleOcrEngine` (it downloaded its detection/recognition/
  angle-classification model weights from PaddleOCR's CDN on first use —
  works from this network), ran `recognize_page` directly against a page
  rasterized from `fixtures/ocr_extraction/sample_contract.pdf` and got
  correct text back at ~99% confidence, then drove a fresh upload through
  the *actual* `POST /api/internal/documents/{id}/reprocess` ->
  `validate_file -> run_ocr -> extract_fields` chain end-to-end with
  `OCR_ENGINE=paddleocr` (the real default, no `null`-engine workaround)
  and confirmed the document reached `complete` with both pages'
  `GET /api/documents/{id}/ocr` output matching the fixture's real text
  and `ocrEngineVersion: "paddleocr:2.9.1"`. Full 57-test suite still
  passes unchanged (paddleocr/paddle are lazy-imported, so the version
  bump doesn't touch anything the unit tests exercise). Not yet updated:
  `fixtures/ocr_extraction/sample_contract.ocr.json`'s golden text was
  captured from a different (fake/fixture) OCR path and doesn't
  byte-for-byte match real paddleocr's output (e.g. `$5,ooo.00` — a
  digit/letter OCR artifact) — `test_regression_fixtures.py` intentionally
  doesn't run against a real engine (see its own docstring), so this
  doesn't affect the test suite, but the golden file is not a claim about
  real paddleocr accuracy.
- ~~`documents.extract_fields`/`generate_embeddings` have never been run
  against a real OpenAI-compatible endpoint~~ Partially resolved: verified
  `OpenAiCompatibleLlmProvider`/`OpenAiCompatibleEmbeddingProvider`'s actual
  HTTP request/response handling against a throwaway local stub server
  (session scratchpad only, not committed) implementing the
  `/chat/completions` and `/embeddings` shapes those providers expect.
  Temporarily pointed the live `celery-worker`/`backend` containers'
  `LLM_BASE_URL`/`EMBEDDING_BASE_URL` at it (`OCR_ENGINE=null` too, since
  paddleocr is blocked -- see above), drove a document through
  `extract_fields` via `/reprocess` and `generate_embeddings` via the new
  `/reindex` (manually seeding one `OcrPage` row through the celery-worker
  container's own DB session, since `OCR_ENGINE=null` produces no text to
  chunk) -- both completed successfully over real HTTP, persisting a real
  `extractions` row (`modelProvider: "openai_compatible"`) and a real
  `chunks` row (`embeddingProvider: "openai_compatible"`), and were then
  exercised through the new Phase 5 Search/Chat APIs end-to-end (approved
  the review, `GET /api/search` and `POST /api/chat` both returned correct,
  citation-backed results against this live data). Reverted `.env` and
  recreated the containers afterward to restore the documented
  fail-fast-without-real-credentials behavior -- this was a one-off
  verification, not a standing change. What this does *not* cover: a real
  OpenAI (or Ollama) account was never used, so response *quality*
  (extraction accuracy, embedding semantic relevance) is still unverified
  — only the transport/parsing code path is now confirmed correct.
- ~~`chunks.embedding` is stored as a JSON float array, not a native
  `pgvector` column~~ Resolved. `Chunk.embedding` is now
  `JSON().with_variant(Vector(settings.embedding_dimensions), "postgresql")`
  (`app/models/chunk.py`) — a real `vector(1536)` column on Postgres,
  JSON on SQLite (keeping the existing test suite unchanged; SQLite has no
  vector type). This was verified as behaviorally transparent *before*
  touching the schema, not assumed: read `pgvector`'s own source
  (`Vector._from_db`/`_to_db` in the installed package) and confirmed both
  directions operate on plain `list[float]`, never a numpy array, so every
  existing caller (`search_service._cosine_similarity`,
  `chunk_repository.upsert_chunk`, the embedding task) needed no changes.
  Migration `0007_chunks_pgvector` (`CREATE EXTENSION IF NOT EXISTS
  vector`, then `ALTER COLUMN ... USING (embedding::text)::vector` —
  pgvector's text form is syntactically a JSON array, so the cast is
  direct, no per-row Python migration) and `0008_chunks_hnsw` (a real HNSW
  index, `vector_cosine_ops` to match `search_service`'s ranking; declared
  on the `Chunk` model too via `Index(...).ddl_if(dialect="postgresql")`
  so it's real DDL on Postgres but skipped on SQLite, and so `alembic
  check` doesn't flag it as drift — the same class of gap fixed for this
  table's other indexes previously). All of this was verified against the
  live Postgres, not just written and assumed correct: rebuilt the images,
  ran the real migration (confirmed `\d chunks` shows `vector(1536)` and
  the `hnsw` index), verified `alembic check` reports no drift and both
  `alembic downgrade -1`/`upgrade head` round-trip cleanly, and — critically
  — caught a real bug this surfaced: `GET /api/search`/`POST /api/chat`
  raised an unhandled 500 when the embedding/LLM provider was unavailable
  (`EmbeddingProviderUnavailable`/`LlmProviderUnavailable` were never
  caught in `app/api/search.py`), now a clean 503. Wrote a correctly
  1536-dim fake embedding through the real `chunk_repository` code path
  against the live native column and confirmed `GET /api/search` returns
  correct cosine-similarity-ranked results reading it back. 3 new tests
  (`test_search_endpoint_503s_when_embedding_provider_unavailable`,
  `test_chat_endpoint_503s_when_embedding_provider_unavailable`,
  `test_chat_endpoint_503s_when_llm_provider_unavailable`,
  `apps/backend/tests/test_search_and_chat.py`, 57 total across the
  backend suite). Not covered: a real embedding model's actual output
  dimension was never used (the stub server used 1536 to match the
  configured default, not because it's semantically an OpenAI embedding);
  a provider/model change to a different output dimension needs its own
  migration, `EMBEDDING_DIMENSIONS` is not auto-detected.
- ~~The document status state machine had no transition back out of
  `complete`/`failed`~~ Resolved: `complete`/`failed -> queued` is now
  allowed and `POST /api/internal/documents/{id}/reprocess` resets and
  re-dispatches the pipeline (see Completed, below). ~~The n8n watchdog
  (`n8n/workflows/02-processing-watchdog.json`) still only surfaces stuck
  documents rather than calling this endpoint automatically -- wiring an
  actual auto-retry policy (vs. an operator-triggered one) is still
  unstarted and deserves its own decision on retry limits/backoff.~~ Also
  resolved: the retry-limit decision was a flat cap
  (`DOCUMENT_AUTO_RETRY_MAX`, default 3), no backoff beyond the watchdog's
  own 10-minute schedule -- the watchdog now calls
  `POST .../auto-retry` for `failed` documents instead of only logging them.
  Stuck `queued`/`processing` documents are still only surfaced, unchanged
  (re-dispatching the same chain wouldn't fix a wedged worker/broker, unlike
  a genuinely `failed` document).

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

- ~~No `n8n/workflows/` entry fronts `/api/chat`~~ Resolved:
  `n8n/workflows/03-rag-chat.json` now does (see Completed, below),
  imported and validated against the real n8n instance. Still inactive by
  default pending the same one-time manual reactivation as `01`/`02`
  (n8n's CLI importer deactivates every workflow it imports). There's also
  no frontend for search/chat (not in Phase 5's PRD scope, so this is
  expected, not a gap against PRD-5's Acceptance Criteria, but users can
  only reach these APIs via `curl`/Swagger/the n8n webhook today). Hybrid
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

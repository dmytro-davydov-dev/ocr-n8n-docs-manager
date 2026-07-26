# Backend

FastAPI service that owns document ingestion, the review state machine, OCR/AI-extraction/embedding orchestration (via Celery), and the hybrid search/chat APIs. See [[architecture/templates/ADR-004-FastAPI-as-Backend-Framework|ADR-004]].

## Location

`apps/backend/`

## Stack

- FastAPI 0.115 + Uvicorn
- SQLAlchemy 2.0 + Alembic (migrations) — see [[database/README|Database]]
- Celery 5.4 + Redis (broker/result backend) — see [[architecture/templates/ADR-008-Celery-for-Background-Processing|ADR-008]]
- PyMuPDF (`fitz`) for PDF validation/rasterization
- PaddleOCR (swappable, see below)
- OpenAI-compatible HTTP clients for LLM extraction and embeddings (swappable)
- pgvector for embedding storage/similarity search

## Structure

```text
apps/backend/
  app/
    main.py              # FastAPI app, router registration, CORS
    core/
      config.py            # Settings (env-driven, see table below)
      database.py           # SQLAlchemy engine/session
      security.py            # internal API key dependency
      logging.py             # logging setup
      storage.py             # local filesystem document storage
    api/                  # routers: health, internal, documents, reviews, search
    models/                # SQLAlchemy ORM models
    schemas/                # Pydantic request/response schemas
    repositories/           # DB access layer (one per model)
    services/                # business logic: document_service, review_service,
                              #   ocr_engine, llm_provider, embedding_provider,
                              #   chunking, search_service, rag_service, ...
    tasks/                  # Celery tasks: file_validation, ocr, extraction, embeddings
    prompts/                # versioned LLM prompt files (ADR-013)
    celery_app.py
  alembic/                # migrations, see [[database/README]]
  tests/                  # unittest suite, see [[testing/Test-Strategy]]
  scripts/                # export_openapi.py, check_openapi_drift.py
  requirements.txt
  Dockerfile
```

## API surface

All routes are mounted under `/api` (`settings.api_prefix`).

- `GET /health` — liveness check, used by Docker healthcheck and `make verify-phase0`.
- `/internal/*` (requires `X-Internal-Api-Key` header, see [[security/README|Security]]):
  - `GET /internal/ping`
  - `POST /internal/documents/{id}/process` — n8n's only entry point into the Celery pipeline (ADR-009); dispatches the `validate_file → run_ocr → extract_fields → generate_embeddings` chain.
  - `POST /internal/documents/{id}/reprocess` — resets a `complete`/`failed` document to `queued` and re-dispatches the chain.
  - `POST /internal/documents/{id}/reindex` — re-runs chunking/embedding only.
  - `PATCH /internal/documents/{id}/status` — n8n reports pipeline progress back; n8n never writes to application tables directly.
- `/documents`:
  - `POST /documents` — upload (validates type/size, stores file, creates `Document`, triggers the n8n webhook).
  - `GET /documents`, `GET /documents/{id}`, `GET /documents/{id}/file`
  - `GET /documents/{id}/ocr`, `GET /documents/{id}/extraction`, `GET /documents/{id}/chunks`
- `/documents/{id}/review/*` — full review lifecycle: `POST` (create), `GET`, `PATCH` (save draft), `POST /submit|/approve|/reject|/revise|/archive`, `GET /history`.
- `/search?q=` — hybrid keyword + vector search over chunks from *approved* reviews only.
- `POST /chat` — RAG Q&A grounded in approved contracts, with citations built directly from retrieved chunks (not LLM self-report).

## Processing pipeline

Every uploaded document moves through Celery tasks chained in this order (`app/tasks/`), each idempotent (re-checks the document's current status before acting, so retries/duplicate dispatch are safe no-ops):

```text
validate_file → run_ocr → extract_fields → generate_embeddings
```

- **OCR engine** — pluggable via `OCR_ENGINE` (`paddleocr` default, `null` no-op for environments without the heavy paddle dependencies). See [[architecture/templates/ADR-010-OCR-Engine-Selection|ADR-010]].
- **LLM provider** — a single OpenAI-compatible HTTP client covers OpenAI, Azure OpenAI, Ollama, and vLLM; swap via `LLM_PROVIDER`/`LLM_BASE_URL`/`LLM_MODEL`. See [[architecture/templates/ADR-012-LLM-Provider-Selection|ADR-012]].
- **Embedding provider** — same pattern, `EMBEDDING_PROVIDER`/`EMBEDDING_BASE_URL`/`EMBEDDING_MODEL`. See [[architecture/templates/ADR-017-Embedding-Model-Strategy|ADR-017]].
- **Chunking** — configurable token limit/overlap (`CHUNK_TOKEN_LIMIT`/`CHUNK_OVERLAP_TOKENS`), whitespace-approximated token count. See [[architecture/templates/ADR-018-Document-Chunking-Strategy|ADR-018]].

## Configuration

All settings live in `app/core/config.py` (`pydantic-settings`, reads `.env`). Key groups: app/log level, `INTERNAL_API_KEY`, CORS origins, `DATABASE_URL`, Celery broker/backend URLs, document storage path/upload limits, n8n webhook URL, OCR/LLM/embedding provider settings, chunking settings, and hybrid-search weights (`SEARCH_KEYWORD_WEIGHT`/`SEARCH_VECTOR_WEIGHT`). See the root [[../../README|README]] env var table for the full list with defaults, and [[docker/README|Docker]] for how these are wired into the running containers.

## Running locally

Via Docker Compose (recommended):

```bash
docker compose up --build backend celery-worker
```

Directly (requires a Python 3.12 venv with `requirements.txt` installed, plus reachable Postgres/Redis):

```bash
cd apps/backend
uvicorn app.main:app --reload
```

## OpenAPI

`packages/api-client/openapi.json` is a generated, checked-in artifact:

```bash
make export-openapi   # regenerate after any route/schema change
make verify-openapi    # CI-enforced drift check
```

The hand-written TypeScript client in `packages/api-client/src/index.ts` is not yet generated from this file — it's a manually-kept mirror of the same contract (tracked as technical debt in [[architecture/Progress.md]]).

## Related

- [[database/README]]
- [[security/README]]
- [[testing/Test-Strategy]]
- [[observability/README]]
- [[architecture/templates/ADR-004-FastAPI-as-Backend-Framework]]
- [[architecture/templates/ADR-008-Celery-for-Background-Processing]]
- [[workstreams/WS-02-Backend-and-Data]]
- [[workstreams/WS-03-Document-Processing-and-OCR]]

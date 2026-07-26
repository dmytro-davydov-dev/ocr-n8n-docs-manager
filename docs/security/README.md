# Security

This is an MVP reference implementation — security controls cover the boundaries that actually matter for the architecture (internal-API isolation, credential isolation, audit trail) rather than end-user auth, which does not exist yet.

## Internal API authentication

Everything under `/api/internal/*` (`apps/backend/app/api/internal.py`) requires an `X-Internal-Api-Key` header matching `INTERNAL_API_KEY` (`app/core/security.py::require_internal_api_key`, a FastAPI dependency applied at the router level). A missing or wrong key returns `401`.

This is the only path n8n has into the backend's write surface (dispatching the Celery pipeline, reporting status back) — n8n never touches the Celery broker or application tables directly ([[architecture/templates/ADR-009-n8n-for-Workflow-Orchestration|ADR-009]]). The corresponding n8n HTTP Request nodes reference an `Internal API Key` credential by id/name only in the committed workflow JSON (`n8n/workflows/`); the actual secret value is entered by hand in the n8n UI after import, not committed. See [[docker/README|Docker]] and `n8n/workflows/README.md`.

`INTERNAL_API_KEY` defaults to `change-me` — must be overridden via `.env` for anything beyond local development.

Test coverage: `apps/backend/tests/test_internal_api_auth.py` (`make test-backend-auth`).

## No end-user authentication yet

The public `/documents`, `/review`, `/search`, `/chat` routes have no auth — anyone who can reach the backend can upload, review, and query contracts. This is acceptable for the current single-tenant local/demo deployment but is a gap before any real deployment; not currently tracked with a specific ADR.

## CORS

`CORS_ORIGINS` (default `http://localhost:5173`) configures FastAPI's `CORSMiddleware` (`app/main.py`) with `allow_credentials=True` and `allow_methods/allow_headers="*"`. Restrict this to the actual frontend origin(s) outside local development.

## Database credential isolation

`n8n` and the application use separate Postgres roles and databases (`N8N_DB_USER`/`N8N_DB_PASSWORD` vs. `POSTGRES_USER`/`POSTGRES_PASSWORD`), each with `CONNECT` denied on the other's database — provisioned by `infra/postgres-init.sh` and verified by `make verify-infra`. Previously n8n and the app shared the same Postgres credentials and only the database name differed; this was tightened as part of WS-05. See [[database/README]].

## Secrets

All secrets (`INTERNAL_API_KEY`, `POSTGRES_PASSWORD`, `N8N_DB_PASSWORD`, `N8N_ENCRYPTION_KEY`, `LLM_API_KEY`, `EMBEDDING_API_KEY`) are supplied via `.env` (gitignored) and consumed as environment variables — none are hardcoded, and `.env.example` documents the keys without real values. `N8N_ENCRYPTION_KEY` in particular protects n8n's own stored credentials (like the `Internal API Key` above) at rest.

## Audit logging

Every mutation to a document or review writes an append-only `audit_log` entry (`AuditLog` model — never updated or deleted): actor, action, entity type/id, and a JSON details blob. This is what lets `GET /documents/{id}/extraction` distinguish "extraction never ran" (404) from "extraction ran and failed schema validation" (422, with the recorded reason), and is the backing data for the review audit-history API (`GET /review/history`). See [[architecture/templates/ADR-015-Audit-Logging-Strategy|ADR-015]] and [[database/README]].

## File upload validation

`POST /documents` restricts content type (`allowed_upload_content_types`, currently PDF only) and size (`MAX_UPLOAD_SIZE_BYTES`, default 50MB), and `validate_file` (the first pipeline task) opens the stored file with PyMuPDF to reject truncated/corrupt PDFs that a content-type check alone would miss.

## Known gaps

- No end-user authentication/authorization (see above).
- `INTERNAL_API_KEY` is a single static shared secret, not per-caller/rotatable.
- No rate limiting on any endpoint.
- No TLS termination configured at the Compose level (expected to sit behind a reverse proxy/load balancer in any real deployment — out of scope for this local stack).

## Related

- [[database/README]]
- [[docker/README]]
- [[backend/README]]
- [[architecture/templates/ADR-009-n8n-for-Workflow-Orchestration]]
- [[architecture/templates/ADR-015-Audit-Logging-Strategy]]
- [[workstreams/WS-05-Infrastructure-and-DevOps]]

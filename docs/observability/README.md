# Observability

Observability today is deliberately minimal — logging and Compose health checks. There is no metrics, tracing, or centralized log aggregation yet.

## Logging

`app/core/logging.py::configure_logging()` (called once at import time in `app/main.py`) configures Python's standard `logging` module: level from `LOG_LEVEL` (default `INFO`), format `%(asctime)s %(levelname)s [%(name)s] %(message)s`. Applies to both the `backend` (FastAPI/Uvicorn) and `celery-worker` processes, since both run the same `app` package.

Logs are not currently shipped anywhere — `docker compose logs -f` (or `make logs`) against stdout/stderr is the only way to view them locally. No structured (JSON) logging, no correlation/request IDs tying a log line to a specific document or Celery task run.

## Health checks

- `GET /api/health` (`app/api/health.py`) — trivial liveness check (`{"status": "ok"}`), used by the `backend` service's Compose `healthcheck` and by `make verify-phase0`.
- `GET /api/internal/ping` — same idea but behind internal-API auth, used to confirm n8n can actually reach the authenticated backend surface (`n8n/workflows/00-internal-api-smoke-test.json`).
- Compose-level health checks also exist for `postgres` (`pg_isready`), `redis` (`redis-cli ping`), and `n8n` (`/healthz`) — see [[docker/README|Docker]].

None of these distinguish "process is up" from "dependencies are healthy" beyond what the check itself probes (e.g. `/api/health` does not verify the database connection).

## Audit log as an observability signal

The `audit_log` table ([[database/README|Database]], [[architecture/templates/ADR-015-Audit-Logging-Strategy|ADR-015]]) is the closest thing to an application-level event trail today: every document/review mutation is recorded with actor, action, and a JSON details blob, and it's queried directly (e.g. `audit_repository.get_latest(..., action="extraction_validation_failed")`) to distinguish "never ran" from "ran and failed" for a given pipeline step. It is not a substitute for structured logging or metrics — it only covers mutations the application explicitly chose to record.

## Operational visibility into the pipeline

- `n8n`'s own UI (execution history) shows the status of each workflow run (`01-document-upload-ingestion`, `02-processing-watchdog`, `03-rag-chat`) — the most direct way to see ingestion/watchdog activity today.
- `02-processing-watchdog.json` polls `GET /api/documents` every 10 minutes and surfaces `failed`/stuck documents in n8n's execution history for manual escalation; it does not page/alert anywhere, and does not automatically retry (see [[architecture/Progress.md]] Blockers).
- Celery task state can be inspected via `celery -A app.celery_app:celery_app inspect ping` (used by `make verify-phase0`) but there is no Flower or equivalent worker dashboard wired up.

## Known gaps

- No metrics (request latency/error rate, queue depth, task duration/failure rate, pipeline stage timing).
- No distributed tracing across FastAPI → Celery → n8n → LLM/embedding provider calls.
- No centralized log aggregation (logs only exist as container stdout).
- No alerting — the watchdog surfaces failures passively in n8n's UI only.
- No correlation ID threading a single document's journey through validate → OCR → extract → embed across log lines.

## Related

- [[docker/README]]
- [[database/README]]
- [[security/README]]
- [[architecture/templates/ADR-015-Audit-Logging-Strategy]]
- [[workstreams/WS-05-Infrastructure-and-DevOps]]

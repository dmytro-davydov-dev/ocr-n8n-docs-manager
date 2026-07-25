# n8n Workflows (WS-04)

Version-controlled source of truth for every n8n workflow (ADR-009). The
n8n runtime's own database is disposable — these JSON exports are what
gets reviewed and deployed. Treat a change to the running workflow that
isn't reflected here as drift.

## Workflows

| File | Phase | Trigger | Purpose |
| --- | --- | --- | --- |
| `00-internal-api-smoke-test.json` | 0 | Manual | Confirms n8n can reach the backend and the `Internal API Key` credential is authenticated. Run once after standing up a new n8n instance. |
| `01-document-upload-ingestion.json` | 1 | Webhook (`POST /webhook/document-uploaded`) | Receives `{document_id}` from the backend's upload-trigger callback (`N8N_WEBHOOK_URL`) and calls `POST /api/internal/documents/{id}/process`, which dispatches the full Celery pipeline (validate → OCR → extract → embed) as one chain. |
| `02-processing-watchdog.json` | 2/3 | Schedule (every 10 min) | Polls `GET /api/documents`, flags documents that are `failed` or stuck in `queued`/`processing` for >15 minutes, and logs them in n8n's execution history for WS-06/operators to act on. Read-only — it does not retry or mutate documents (a `failed`/`complete` → `queued` transition and `POST /api/internal/documents/{id}/reprocess` now exist on the backend; this workflow still only surfaces stuck documents rather than calling it automatically — see `docs/architecture/Progress.md` Technical Debt). |
| `03-rag-chat.json` | 5 | Webhook (`POST /webhook/rag-chat`) | Fronts the backend's retrieval-grounded Q&A (`POST /api/chat`) as an observable workflow, per ADR-020: n8n owns orchestration/logging, retrieval + prompt construction + citations stay backend-side. `{"question": "..."}` in, `{answer, citations, model}` out (or 404 if nothing indexed matches). Unlike `01`/`02`, this calls a **public** backend endpoint — no `Internal API Key` credential required. |

Every workflow calls WS-02's internal API only — none of them write to
application tables or touch the Celery broker directly (ADR-009, WS-04
Done Criteria).

## Required credential

All HTTP Request nodes authenticate with an **HTTP Header Auth** credential
named `Internal API Key` (referenced in the exported JSON by id
`internal-api-key`, name only — no secret value is ever exported):

- Header name: `X-Internal-Api-Key`
- Header value: the same value as the backend's `INTERNAL_API_KEY` env var

Create this credential by hand in the n8n UI (Credentials → New →
HTTP Header Auth) after import; it is not part of the JSON export and must
never be committed.

`01`, `02`, and `03` are exported `active: true`, but n8n's CLI importer
deactivates every workflow it imports regardless of credentials
("Deactivating workflow ... Remember to activate later" in the container
logs/CLI output — confirmed directly with `n8n import:workflow`, not just
inferred). `01`/`02` additionally can't do anything useful until the
`Internal API Key` credential below exists (`03` doesn't need it — see
table above). Create the credential if needed, then reactivate from the
n8n UI (Active toggle) or `n8n update:workflow --active=true --id=<id>`.

## Importing

```bash
docker compose exec n8n n8n import:workflow --separate --input=/workflows
```

`docker-compose.yml` mounts `./n8n/workflows:/workflows:ro` into the `n8n`
service and runs this import automatically on every container start
(`command:` in `docker-compose.yml`), so the committed JSON is the source
of truth on restart, not a manual step for the compose stack. Only run the
command above by hand for an out-of-band import (e.g. against a different
n8n instance).

## Idempotency

- `01-document-upload-ingestion`: safe under duplicate webhook delivery.
  Every task in the dispatched Celery chain re-checks the document's
  current status before acting, so re-dispatching against a document
  that's already mid-pipeline or complete is a chain of no-ops, not a
  duplicate run.
- `02-processing-watchdog`: read-only, so re-running has no side effects
  beyond appearing again in the execution log.
- `03-rag-chat`: read-only (a question in, an answer out); no state to
  duplicate on retry.

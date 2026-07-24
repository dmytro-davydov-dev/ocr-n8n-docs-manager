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
| `02-processing-watchdog.json` | 2/3 | Schedule (every 10 min) | Polls `GET /api/documents`, flags documents that are `failed` or stuck in `queued`/`processing` for >15 minutes, and logs them in n8n's execution history for WS-06/operators to act on. Read-only — it does not retry or mutate documents (there is currently no `failed`/`complete` → requeue transition on the backend; see `docs/architecture/Progress.md` Technical Debt). |

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

`01` and `02` are exported `active: true`, but n8n auto-deactivates any
workflow on import if the credential it references doesn't exist yet
("Deactivating workflow ... Remember to activate later" in the container
logs) — expected on first boot, before the credential above has been
created. Create the credential, then reactivate both workflows from the
n8n UI (Active toggle) or `n8n update:workflow --active=true --id=<id>`.

## Importing

```bash
docker compose exec n8n n8n import:workflow --separate --input=/workflows
```

(the `n8n` service mounts `documents:/documents`, not this directory — for
local import, either add a bind mount for `./n8n/workflows:/workflows` or
import through the n8n UI instead).

## Idempotency

- `01-document-upload-ingestion`: safe under duplicate webhook delivery.
  Every task in the dispatched Celery chain re-checks the document's
  current status before acting, so re-dispatching against a document
  that's already mid-pipeline or complete is a chain of no-ops, not a
  duplicate run.
- `02-processing-watchdog`: read-only, so re-running has no side effects
  beyond appearing again in the execution log.

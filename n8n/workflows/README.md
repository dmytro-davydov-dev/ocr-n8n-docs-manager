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
| `02-processing-watchdog.json` | 2/3 | Schedule (every 10 min) | Polls `GET /api/documents`. `failed` documents are automatically retried via `POST /api/internal/documents/{id}/auto-retry`, bounded by the backend's `DOCUMENT_AUTO_RETRY_MAX` (default 3) so this can't loop forever — once exhausted the backend returns 409 and the workflow just logs it. Documents stuck in `queued`/`processing` for >15 minutes are still only logged in n8n's execution history for a human, since re-dispatching the same pipeline wouldn't fix a wedged worker/broker. |
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

**This is now created automatically** by `infra/n8n-bootstrap.sh`, which the
`n8n` service runs on every container start in place of a bare
`n8n import:workflow`. It renders `infra/n8n-credentials.template.json`
(committed, placeholder value only) with the container's own
`INTERNAL_API_KEY` env var via `sed`, imports it with
`n8n import:credentials`, then imports the workflows and reactivates `01`,
`02`, and `03` with `n8n update:workflow --active=true --id=<id>` — n8n's CLI
importer deactivates every workflow it imports regardless of credentials
("Deactivating workflow ... Remember to activate later" in the container
logs — confirmed directly with `n8n import:workflow`, not just inferred), so
reactivation has to be explicit either way. No secret is ever written to a
file that survives past the container's `/tmp` (removed immediately after
import) or committed to the repo.

For an out-of-band import against a different n8n instance, the credential
still needs to exist by hand (Credentials → New → HTTP Header Auth) — the
bootstrap script only wires up the compose stack.

## Importing

```bash
docker compose exec n8n n8n import:workflow --separate --input=/workflows
```

`docker-compose.yml` mounts `./n8n/workflows:/workflows:ro` and
`./infra/n8n-bootstrap.sh` into the `n8n` service and runs the bootstrap
script automatically on every container start (`command:` in
`docker-compose.yml`), so the committed JSON is the source of truth on
restart, not a manual step for the compose stack. Only run the command above
by hand for an out-of-band import (e.g. against a different n8n instance).

## Idempotency

- `01-document-upload-ingestion`: safe under duplicate webhook delivery.
  Every task in the dispatched Celery chain re-checks the document's
  current status before acting, so re-dispatching against a document
  that's already mid-pipeline or complete is a chain of no-ops, not a
  duplicate run.
- `02-processing-watchdog`: safe to re-run. The Auto Retry call goes through
  `POST .../auto-retry`, which is bounded by `DOCUMENT_AUTO_RETRY_MAX` and
  only acts on documents currently `failed` — a document that's already been
  re-dispatched (now `queued`/`processing`) or has exhausted its retry budget
  gets a 409 on the next sweep instead of a duplicate dispatch. Stuck-document
  logging remains read-only, as before.
- `03-rag-chat`: read-only (a question in, an answer out); no state to
  duplicate on retry.

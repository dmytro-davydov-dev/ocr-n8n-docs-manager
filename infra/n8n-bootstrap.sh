#!/bin/sh
# WS-04: bootstraps a fresh n8n instance so a plain `docker compose up` isn't
# DOA (see docs/architecture/Progress.md Blockers #1). Historically this
# required a human to open the n8n UI and hand-create the "Internal API Key"
# HTTP Header Auth credential, then reactivate `01`/`02`/`03` after n8n's CLI
# importer deactivates every workflow it imports regardless of credentials.
# Both steps are scripted here instead.
set -eu

# The credential's secret value comes from the same INTERNAL_API_KEY env var
# the backend/celery-worker use -- never hardcoded, never committed. Only the
# templated id/name/header-name are checked in (infra/n8n-credentials.template.json).
sed "s/__INTERNAL_API_KEY__/${INTERNAL_API_KEY}/" \
  /docker-entrypoint-n8n/n8n-credentials.template.json > /tmp/n8n-credentials.json

n8n import:credentials --input=/tmp/n8n-credentials.json
rm -f /tmp/n8n-credentials.json

n8n import:workflow --separate --input=/workflows

# n8n's CLI importer deactivates every workflow it imports, confirmed via its
# own "Deactivating workflow ... Remember to activate later" log output --
# reactivate explicitly instead of leaving this as a manual UI step.
n8n update:workflow --active=true --id=ws04-01-document-upload-ingestion
n8n update:workflow --active=true --id=ws04-02-processing-watchdog
n8n update:workflow --active=true --id=ws05-03-rag-chat

exec n8n

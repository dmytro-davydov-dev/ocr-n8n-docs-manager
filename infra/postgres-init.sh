#!/bin/bash
# WS-05: runs once, on first init of an empty postgres_data volume (ADR-002).
set -euo pipefail

# ADR-016: pgvector extension on the application database, so WS-02/WS-03 can
# migrate chunks.embedding from a JSON column to a real `vector` column later.
# Also lock CONNECT down to the app role -- Postgres grants CONNECT on every
# database to PUBLIC by default, which would otherwise let the n8n role below
# connect to the app's database despite having no table grants there.
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS vector;
    REVOKE CONNECT ON DATABASE "${POSTGRES_DB}" FROM PUBLIC;
    GRANT CONNECT ON DATABASE "${POSTGRES_DB}" TO "${POSTGRES_USER}";
EOSQL

# WS-05 Done Criteria: application and n8n persistence must use separate
# credentials, not just separate database names. n8n gets its own role,
# scoped to only its own database -- it cannot connect to or touch the app's
# database at all.
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    CREATE USER "${N8N_DB_USER}" WITH PASSWORD '${N8N_DB_PASSWORD}';
    CREATE DATABASE "${N8N_DB_NAME}" OWNER "${N8N_DB_USER}";
    REVOKE CONNECT ON DATABASE "${N8N_DB_NAME}" FROM PUBLIC;
    GRANT ALL PRIVILEGES ON DATABASE "${N8N_DB_NAME}" TO "${N8N_DB_USER}";
EOSQL

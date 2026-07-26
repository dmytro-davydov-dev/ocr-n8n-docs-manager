# Database

PostgreSQL 16 (via the `pgvector/pgvector:pg16` image) is the primary datastore. See [[architecture/templates/ADR-006-PostgreSQL-as-Primary-Database|ADR-006]] and [[architecture/templates/ADR-016-Vector-Database-Selection|ADR-016]] (why pgvector rather than a separate vector DB).

## Schema

Managed by SQLAlchemy models (`apps/backend/app/models/`) and versioned via Alembic (`apps/backend/alembic/versions/`). All primary keys are `String(36)` UUID text (not Postgres's native `UUID` type) so the same models also run against SQLite in the unit test suite.

| Table | Model | Notes |
| --- | --- | --- |
| `documents` | `Document` | One row per upload. `status` ∈ `uploaded, queued, processing, complete, failed`; transitions enforced by `document_repository.ALLOWED_TRANSITIONS` (includes `complete/failed → queued` for reprocessing). Indexed on `status`, `content_hash`. |
| `audit_log` | `AuditLog` | Append-only, never updated/deleted. One entry per mutation across the system ([[architecture/templates/ADR-015-Audit-Logging-Strategy\|ADR-015]]). Indexed on `(entity_type, entity_id)`. |
| `reviews` | `Review` | One active review per document (`document_id` unique). `status` ∈ `draft_review, in_review, approved, rejected, archived` ([[architecture/templates/ADR-014-Review-State-Management\|ADR-014]]). Optimistic locking via a `version` counter. |
| `review_revisions` | `ReviewRevision` | Append-only snapshot of a `Review` at each version/status change — the audit-history trail returned by `GET /review/history`. |
| `ocr_pages` | `OcrPage` | Page-level OCR output, one row per `(document_id, page_number)`, upserted on re-OCR ([[architecture/templates/ADR-011-OCR-Storage-Strategy\|ADR-011]]). |
| `extractions` | `Extraction` | One row per document, upserted on re-extraction. Records `prompt_id`/`prompt_version`/`model_provider`/`model_name` with every result ([[architecture/templates/ADR-013-Prompt-Management-Strategy\|ADR-013]]). |
| `chunks` | `Chunk` | RAG chunks + embeddings, unique on `(document_id, chunk_index)`, upserted on re-chunk/re-embed; stale trailing chunks from a prior run are dropped. `embedding` is a native `vector(1536)` column on Postgres (JSON array on SQLite) with an HNSW index (`vector_cosine_ops`) — see below. |

JSON-typed columns (`content`, `details`, etc.) use `JSON().with_variant(JSONB(), "postgresql")` — JSONB on Postgres, portable JSON on SQLite.

## Migrations

```text
0001_init                                — baseline schema
0002_documents_and_audit_log
0003_reviews
0004_ocr_pages
0005_extractions
0006_chunks                              — chunks table, JSON embedding column
0007_chunks_pgvector                     — chunks.embedding → native vector(1536)
0008_chunks_embedding_hnsw_index          — HNSW index, vector_cosine_ops
```

Run migrations:

```bash
cd apps/backend
alembic upgrade head
alembic check     # detects model/migration drift; CI-enforced
```

In the running stack, `backend`'s container command applies migrations automatically on start (`alembic upgrade head && uvicorn ...`, see `docker-compose.yml`).

`alembic check` has previously caught real drift — several indexes were declared via `op.create_index(...)` in migrations but not on the corresponding model columns, which would have been silently dropped by a future autogenerate. Any new index must be added to both the migration and the model (the model can guard Postgres-only DDL like the HNSW index with `.ddl_if(dialect="postgresql")` so it's skipped against SQLite).

## pgvector

Enabled per-database by `infra/postgres-init.sh` (`CREATE EXTENSION IF NOT EXISTS vector`) on first init of the `postgres_data` volume — see [[docker/README|Docker]]. `chunks.embedding` is `vector(1536)` (`EMBEDDING_DIMENSIONS` setting, must match whatever `EMBEDDING_MODEL` actually produces — a model/provider change to a different output dimension needs its own migration; the dimension is not auto-detected). The HNSW index uses `vector_cosine_ops` to match `search_service`'s cosine-similarity ranking ([[architecture/templates/ADR-019-Hybrid-Retrieval-Strategy|ADR-019]]).

## Isolation from n8n

`n8n` uses a separate Postgres database and role (`N8N_DB_NAME`/`N8N_DB_USER`/`N8N_DB_PASSWORD`) provisioned by the same init script, with `CONNECT` revoked on the app database and vice versa — n8n never has any access to application tables, consistent with it only reaching the backend through the authenticated internal API ([[architecture/templates/ADR-009-n8n-for-Workflow-Orchestration|ADR-009]]). Verified by `make verify-infra`.

## Local access

```bash
docker compose exec postgres psql -U postgres -d contracts
```

Default connection string (see `DATABASE_URL` in the root README's env var table): `postgresql+psycopg2://postgres:postgres@postgres:5432/contracts`.

## Testing

The backend unit test suite runs against an in-memory SQLite database (`sqlalchemy.create_engine("sqlite:///:memory:", ...)`), not Postgres — this keeps tests fast and dependency-free but means pgvector-specific behavior (the native `vector` type, the HNSW index) is only exercised against a real Postgres in CI's migration step and in manual live-stack verification, not in the unit tests themselves. See [[testing/Test-Strategy]].

## Related

- [[backend/README]]
- [[security/README]] (n8n database isolation as a security control)
- [[architecture/templates/ADR-006-PostgreSQL-as-Primary-Database]]
- [[architecture/templates/ADR-016-Vector-Database-Selection]]
- [[architecture/templates/ADR-018-Document-Chunking-Strategy]]
- [[workstreams/WS-02-Backend-and-Data]]

# Docker

Local stack orchestration via Docker Compose. See [[architecture/templates/ADR-002-Docker-Compose|ADR-002]] for why Compose (not Kubernetes) at this stage.

## Services

Defined in `docker-compose.yml` (repo root):

| Service | Image / Build | Port | Purpose |
| --- | --- | --- | --- |
| `frontend` | `apps/frontend/Dockerfile` (node:20-alpine) | 5173 | Vite dev server |
| `backend` | `apps/backend/Dockerfile` (python:3.12-slim) | 8000 | FastAPI app; runs `alembic upgrade head` then `uvicorn` on start |
| `celery-worker` | `apps/backend/Dockerfile` (same image, different command) | — | Runs the OCR/extraction/embedding task chain |
| `postgres` | `pgvector/pgvector:pg16` | 5432 | Primary datastore; pgvector extension enabled ([[architecture/templates/ADR-006-PostgreSQL-as-Primary-Database\|ADR-006]], [[architecture/templates/ADR-016-Vector-Database-Selection\|ADR-016]]) |
| `redis` | `redis:7-alpine` | 6379 | Celery broker + result backend ([[architecture/templates/ADR-007-Redis-as-Cache-and-Message-Broker\|ADR-007]]) |
| `n8n` | `n8nio/n8n:1.71.3` | 5678 | Workflow orchestration ([[architecture/templates/ADR-009-n8n-for-Workflow-Orchestration\|ADR-009]]); auto-imports `n8n/workflows/` on every start |

Named volumes: `postgres_data`, `n8n_data`, `documents` (shared by `backend`, `celery-worker`, and `n8n` for uploaded files).

## Dependency graph & health checks

`backend` waits on `postgres`/`redis` (`service_healthy`); `frontend` waits on `backend`; `n8n` waits on `postgres`. Each of `postgres`, `redis`, `backend`, and `n8n` defines a Compose `healthcheck` (`pg_isready`, `redis-cli ping`, `curl /api/health`, and an n8n `/healthz` fetch via `node -e`, respectively), so `docker compose up` brings the stack up in the correct order rather than racing.

## Backend/celery-worker image

`apps/backend/Dockerfile` (python:3.12-slim): installs `build-essential`, `libpq-dev`, `curl`, and — required by PaddleOCR's `cv2` dependency — `libgl1`/`libglib2.0-0`. `backend` and `celery-worker` share this image but run different commands (`uvicorn` vs. `celery ... worker`).

## Frontend image

`apps/frontend/Dockerfile` (node:20-alpine): installs the workspace's `packages/api-client` alongside `apps/frontend`, then runs `npm run dev` (dev server, not a production build — there is no production Dockerfile/nginx stage yet).

## Postgres init

`infra/postgres-init.sh` runs once, on first init of an empty `postgres_data` volume:

- Enables the `vector` extension on the application database and revokes default `PUBLIC` `CONNECT` (Postgres grants `CONNECT` on every database to `PUBLIC` by default).
- Creates a dedicated `n8n` Postgres role/database (`N8N_DB_USER`/`N8N_DB_PASSWORD`), isolated from the application's own credentials — n8n cannot connect to or touch the app database, and vice versa. Verified by `make verify-infra`.

## Commands

```bash
docker compose up --build      # start everything, rebuilding images
docker compose down             # stop
docker compose down -v          # stop and wipe volumes (full reset)
docker compose logs -f          # follow logs
```

Via the Makefile (thin wrappers plus verification targets):

```bash
make up / make down / make reset / make logs
make verify-phase0    # compose config validity + frontend/backend/n8n/postgres/redis/celery reachability
make verify-infra      # pgvector extension present; n8n's Postgres role is isolated from the app db
make test-backend-auth # apps/backend/tests/test_internal_api_auth.py
make test-backend       # full backend unittest suite
make export-openapi / make verify-openapi
```

`test-backend*`/`export-openapi`/`verify-openapi` run against a local Python venv if `fastapi` is importable there, otherwise they fall back to `docker compose run --rm backend ...` — keep the backend image rebuilt (`docker compose build backend celery-worker`) if you rely on the fallback, since a stale image has previously caused it to run a smaller/older test suite than the local venv (see [[architecture/Progress.md]]).

## Environment variables

Copy `.env.example` to `.env` at the repo root; Compose interpolates every `${VAR:-default}` in `docker-compose.yml` from it. The full variable list (Postgres, n8n, OCR/LLM/embedding providers, chunking, search weights, worker resource limits, etc.) is documented in the root [[../../README|README]]'s environment variable table — that table is the source of truth, not this page, to avoid the two drifting.

One documented failure mode worth knowing: a setting can be present in `.env`/`.env.example`/the README table without actually being forwarded into a service's `environment:` block in `docker-compose.yml` — this happened for several OCR/LLM/embedding/chunking variables and for `VITE_ENABLE_API_MOCKS` (both fixed, see [[architecture/Progress.md]] Completed log). If a config change to `.env` appears to have no effect, check that the variable is actually listed under the relevant service in `docker-compose.yml`.

## Worker resource limits

`celery-worker` sets `deploy.resources.limits/reservations` (CPU/memory) since OCR is CPU-heavy, tunable via `WORKER_CPU_LIMIT`/`WORKER_MEMORY_LIMIT`/`WORKER_CPU_RESERVATION`/`WORKER_MEMORY_RESERVATION`.

## Related

- [[backend/README]]
- [[database/README]]
- [[security/README]]
- [[architecture/templates/ADR-002-Docker-Compose]]
- [[workstreams/WS-05-Infrastructure-and-DevOps]]

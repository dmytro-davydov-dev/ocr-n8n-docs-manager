# WS-05 — Infrastructure and DevOps

**Status:** Accepted
**Date:** 2026-07-24
**Owner:** Platform Team

---

# Purpose

Own the foundation every other workstream runs on: repository layout, Docker Compose topology, environment configuration, persistent volumes, health checks, and the monorepo's structural rules. Nothing in WS-01–WS-04 ships without this workstream's containers, network, and storage.

---

# Scope

- Root-level: `docker-compose.yml`, `Makefile`, `.env.example`, `.gitignore` (ADR-002).
- Repository structure and directory ownership (ADR-001, ADR-003).
- Service definitions: frontend, api, worker, postgres, redis, n8n, optional Ollama.
- Named volumes: `postgres_data`, `document_data`, `n8n_data`, `ollama_data`.
- Health checks for PostgreSQL, Redis, FastAPI, n8n.
- Vector database provisioning: pgvector extension on PostgreSQL (ADR-016).
- Environment variable documentation (README table) and `.env.example` upkeep.

---

# Responsibilities

- Keep every service reachable via Compose service names, never `localhost`.
- Ensure persistent volumes survive container restarts.
- Provision separate credentials/databases for application vs. n8n data (ADR-006).
- Add services/volumes/env vars additively within a phase; treat structural topology changes as requiring an ADR update.
- Own `make verify-phase0` and equivalent phase-verification tooling.
- Provision the shared document storage volume consumed by WS-02 and WS-03.

---

# Out of Scope

- Application code inside any service (owned by WS-01/02/03/04).
- Business logic, schema design (WS-02 owns the schema; WS-05 owns that Postgres itself runs and is healthy).
- Kubernetes or production deployment automation (explicitly deferred, ADR-002).

---

# Deliverables

- `docker-compose.yml`, Dockerfiles, `.env.example`, `Makefile` (Phase 0).
- Shared document storage volume (Phase 1).
- OCR engine container/resources (Phase 2).
- Provider/model configuration plumbing for LLM and embedding providers (Phase 3/5).
- pgvector-enabled PostgreSQL for vector search (Phase 5).

---

# Dependencies

- **No dependency on other workstreams** — this is the foundation layer; it depends only on Docker/Docker Compose being available on the host.
- **Depended on by all other workstreams.** Changes here should be communicated proactively since they can block everyone simultaneously.

---

# Consumes

- Nothing from other workstreams by design.

# Produces

- The running Compose stack: frontend, api, worker, postgres, redis, n8n containers and their network.
- Named volumes for durable data.
- Documented environment variables (`.env.example`, README table).
- Health-check status that WS-06's `make verify-phase0` and CI depend on.

---

# Milestones by Phase

| Phase | Milestone |
|---|---|
| 0 | `docker compose up --build` starts every service; all health checks pass. |
| 1 | Shared document storage volume mounted and writable by api + worker. |
| 2 | OCR engine resourced (CPU/memory) and reachable from the worker. |
| 3 | LLM/embedding provider credentials and endpoints configurable via env, no code changes. |
| 5 | pgvector extension enabled; vector indexes creatable. |

---

# Done Criteria

- One command (`docker compose up --build`) reproduces the full stack on a clean machine.
- All required health checks are green.
- No service uses `localhost` to reach another service.
- Application and n8n persistence are isolated (separate DB/schema/credentials).
- No secrets committed; `.env.example` stays authoritative and current.

---

# Risks

| Risk | Mitigation |
|---|---|
| Docker configuration drift | Keep everything in Compose; no undocumented manual steps. |
| Service startup order issues | Health checks + `depends_on: condition: service_healthy`. |
| Local resource exhaustion (disk/CPU) | Document resource requirements; pin image digests if needed. |
| Config inconsistency across environments | Single `.env.example` as source of truth. |

---

# Future Evolution

- Compose profiles for optional services (e.g., Ollama).
- Dev containers for consistent editor tooling.
- Kubernetes manifests / Helm charts if production deployment requires it (deferred, not planned for MVP).

---

# Related Documents

- [[README]]
- [[../MOC]]
- [[../templates/ADR-001-Monorepo]]
- [[../templates/ADR-002-Docker-Compose]]
- [[../templates/ADR-003-Repository-Structure]]
- [[../templates/ADR-016-Vector-Database-Selection]]
- [[../templates/PRD-Phase-0-Foundation]]

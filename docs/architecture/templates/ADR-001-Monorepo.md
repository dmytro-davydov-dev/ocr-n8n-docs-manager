# ADR-001 — Monorepo

- **Status:** Accepted
- **Date:** YYYY-MM-DD
- **Decision Makers:** Project Team

---

# Context

The MVP consists of several tightly-coupled components:

- React frontend
- FastAPI backend
- Celery worker
- n8n workflows
- Docker Compose
- PostgreSQL and Redis
- Shared documentation (PRDs, ADRs, architecture)
- Shared API contracts

These components evolve together and are released together.

---

# Decision

Adopt a **monorepo**.

The repository will contain application code, infrastructure, workflows, documentation, fixtures, and shared packages.

High-level layout:

```text
apps/
  frontend/
  backend/

packages/
  api-client/

n8n/
infra/
docs/
fixtures/
```

---

# Rationale

A monorepo provides:

- atomic cross-stack changes;
- single-version releases;
- one Docker Compose environment;
- simple onboarding;
- unified CI/CD;
- version-controlled n8n workflows;
- co-located documentation and implementation.

---

# Alternatives Considered

## Multiple repositories

Pros

- independent release cadence
- isolated permissions

Cons

- duplicated configuration
- harder local setup
- synchronized versioning required
- more complex CI

Rejected for the MVP.

---

# Consequences

Positive

- Easier developer experience.
- Simpler Docker Compose configuration.
- Shared API contracts.
- Unified pull requests.
- Better fit for an architecture knowledge base.

Negative

- Repository grows over time.
- CI may become slower.
- Strong folder boundaries must be maintained.

---

# Repository Rules

- Backend owns business logic.
- n8n owns workflow orchestration only.
- Frontend communicates only with FastAPI.
- API contracts are generated from OpenAPI.
- Infrastructure lives under `infra/`.
- Documentation lives under `docs/`.

---

# Future Evolution

The repository may be split only if:

- independent teams own services;
- services have separate release cycles;
- deployment pipelines diverge significantly.

Until then, the monorepo remains the preferred architecture.

---

# Related Documents

- [[../MOC]]
- [[../architecture/Progress]]
- [[../prd/PRD-Phase-0-Foundation]]

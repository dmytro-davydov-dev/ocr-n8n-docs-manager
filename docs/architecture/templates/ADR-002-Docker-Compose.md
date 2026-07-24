# ADR-002 — Docker Compose as the Local Development Platform

**Status:** Accepted  
**Version:** 1.0  
**Date:** YYYY-MM-DD  
**Owner:** Engineering

---

# Context

The Contract Review MVP consists of multiple services that must work together:

- React frontend
- FastAPI API
- Celery worker
- n8n
- PostgreSQL
- Redis
- Optional Ollama
- Shared document storage

Developers should be able to start the complete environment with a single command, regardless of host operating system.

---

# Decision

Use **Docker Compose** as the standard local development and integration environment.

Every service required to run the MVP will be defined in a single `docker-compose.yml` located at the project root.

Docker Compose becomes the canonical local runtime for development, integration testing, and demonstrations.

---

# Goals

- One-command startup.
- Reproducible development environment.
- Consistent service networking.
- Persistent local data.
- Minimal host machine dependencies.
- Easy onboarding.

---

# Service Topology

```text
frontend
    │
    ▼
FastAPI
    │
    ├── PostgreSQL
    ├── Redis
    ├── n8n
    └── Celery Worker
             │
             ▼
      OCR + AI Processing

Optional:
Ollama
```

---

# Compose Services

| Service | Responsibility |
|---------|----------------|
| frontend | React application |
| api | Public REST API |
| worker | Celery processing |
| postgres | Application and n8n databases |
| redis | Celery broker |
| n8n | Workflow orchestration |
| ollama (optional) | Local LLM |

---

# Networking

Services communicate using Docker Compose service names.

Examples:

```text
api → postgres
api → redis
api → n8n

worker → postgres
worker → redis

n8n → api
frontend → api
```

No service-to-service communication should use `localhost`.

---

# Persistent Volumes

Use named Docker volumes for:

- postgres_data
- document_data
- n8n_data
- ollama_data (optional)

Uploaded contracts must survive container restarts.

---

# Environment Configuration

All configuration is supplied through:

- `.env`
- `.env.example`

No secrets are committed to source control.

---

# Health Checks

Every long-running service should expose a health check where possible.

Required:

- PostgreSQL
- Redis
- FastAPI
- n8n

Compose dependencies should use health status rather than startup order alone.

---

# Alternatives Considered

## Native host installation

Pros

- Slightly faster startup.

Cons

- OS-specific setup.
- Dependency drift.
- Harder onboarding.

Rejected.

---

## Kubernetes (local)

Pros

- Closer to production.

Cons

- Much higher operational complexity.
- Slower iteration.
- Unnecessary for the MVP.

Deferred until later.

---

# Consequences

## Positive

- Identical environments across developers.
- Easy onboarding.
- Simple integration testing.
- Easy CI reuse.
- Predictable networking.

## Negative

- Higher resource usage.
- Longer initial image builds.
- Docker becomes a required dependency.

---

# Repository Impact

Project root contains:

```text
docker-compose.yml
.env.example
Makefile
```

Service-specific Dockerfiles remain inside their respective applications.

---

# Acceptance Criteria

- `docker compose up --build` starts the stack.
- Services become healthy.
- Frontend can reach FastAPI.
- FastAPI can reach PostgreSQL, Redis, and n8n.
- Worker can process queued jobs.
- Persistent volumes survive restart.
- New developers require no manual service installation beyond Docker.

---

# Future Evolution

Potential future improvements:

- Compose profiles.
- Dev containers.
- Kubernetes manifests.
- Helm charts.
- Production deployment automation.

Docker Compose remains the reference local development environment even if production later moves to Kubernetes.

---

# Related Documents

- [[../MOC]]
- [[../architecture/Progress]]
- [[ADR-001-Monorepo]]
- [[../prd/PRD-Phase-0-Foundation]]

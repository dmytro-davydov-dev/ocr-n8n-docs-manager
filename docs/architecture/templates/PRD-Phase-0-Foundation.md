
# PRD — Phase 0: Foundation

**Version:** 1.0  
**Status:** Draft  
**Owner:** Engineering

---

# 1. Purpose

Phase 0 establishes the technical foundation for the Contract Review MVP. No business functionality is delivered in this phase; instead, it creates the infrastructure, repository structure, development workflow, and architectural boundaries that every later phase depends on.

---

# 2. Goals

The outcome of this phase is a fully reproducible local development environment started with a single command:

```bash
docker compose up --build
```

All core services must be running and able to communicate.

---

# 3. In Scope

## Repository

- Monorepo structure
- Documentation structure
- Obsidian knowledge base
- Architecture Decision Records (ADR)
- Product Requirements Documents (PRD)

## Frontend

- React + TypeScript + Vite
- Material UI
- React Router
- TanStack Query
- Application shell
- API client abstraction
- Error boundary

## Backend

- FastAPI
- SQLAlchemy
- Alembic
- Pydantic Settings
- Logging
- Health endpoint
- Internal API authentication

## Infrastructure

- Docker Compose
- PostgreSQL
- Redis
- Celery worker
- n8n
- Shared document volume
- Environment configuration
- Health checks

---

# 4. Out of Scope

- PDF upload
- OCR
- AI extraction
- LLM integration
- Review UI
- Authentication
- Email integration

---

# 5. Functional Requirements

FR-001 Repository follows the approved monorepo layout.

FR-002 Docker Compose starts every service.

FR-003 Frontend is reachable in a browser.

FR-004 Backend exposes `/api/health`.

FR-005 PostgreSQL migrations execute successfully.

FR-006 Celery connects to Redis.

FR-007 n8n starts and persists its state in PostgreSQL.

FR-008 Shared document storage is mounted.

FR-009 Environment variables are documented.

---

# 6. Non-functional Requirements

- One-command startup.
- Repeatable local environment.
- Cross-platform support (macOS/Linux).
- Version-controlled infrastructure.
- Containerized services.
- Clear service boundaries.
- Structured logging.
- Local-first development.

---

# 7. Deliverables

- Repository structure
- Dockerfiles
- docker-compose.yml
- Makefile
- .env.example
- React application shell
- FastAPI application shell
- Celery worker
- PostgreSQL
- Redis
- n8n
- Initial database migration
- Project documentation

---

# 8. Dependencies

None.

This is the foundation for all subsequent phases.

---

# 9. Risks

| Risk | Mitigation |
|------|------------|
| Docker configuration drift | Keep everything in Compose |
| Service startup order | Health checks and dependencies |
| Repository disorder | Enforce documented structure |
| Configuration inconsistency | Single `.env.example` |

---

# 10. Acceptance Criteria

- `docker compose up --build` completes successfully.
- Frontend is available.
- Backend health endpoint responds.
- PostgreSQL is initialized.
- Redis accepts connections.
- Celery worker starts.
- n8n is reachable.
- n8n uses PostgreSQL for persistence.
- Repository matches the documented structure.
- Documentation is committed.

---

# 11. Related ADRs

- [[../adr/ADR-001-Monorepo]]
- [[../adr/ADR-002-Docker-Compose]]
- [[../adr/ADR-003-Repository-Structure]]
- [[../adr/ADR-004-FastAPI]]
- [[../adr/ADR-005-React]]
- [[../adr/ADR-006-PostgreSQL]]
- [[../adr/ADR-007-Redis]]
- [[../adr/ADR-008-Celery]]
- [[../adr/ADR-009-n8n]]

---

# 12. Related Documents

- [[../MOC]]
- [[../architecture/Progress]]
- [[../implementation/High-Level-Implementation-Plan]]

---

# 13. Exit Criteria

Phase 0 is complete when every developer can clone the repository, run a single Docker Compose command, and obtain a fully functioning local development environment without manual configuration.

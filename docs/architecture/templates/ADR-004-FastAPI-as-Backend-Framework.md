# ADR-004 — FastAPI as Backend Framework

- **Status:** Accepted
- **Date:** 2026-07-24
- **Decision Makers:** Project Team

---

# Context

The Contract Review MVP requires a backend that exposes the public application API, owns business rules, persists document-processing state, and coordinates internal processing components.

The backend must support:

- REST endpoints for frontend integration;
- asynchronous document-processing workflows;
- Python-native OCR and AI libraries;
- OpenAPI generation;
- request and response validation;
- SQLAlchemy and Alembic integration;
- structured configuration and logging;
- Docker-based local development;
- internal API authentication between FastAPI, n8n, and workers.

The application is a document-processing and AI-oriented system. Keeping the API layer in Python reduces cross-language boundaries between the API, OCR pipeline, Celery tasks, and AI integrations.

---

# Decision

Use **FastAPI** as the backend framework for the Contract Review MVP.

The FastAPI application is located under:

```text
apps/backend/app/
```

It is the authoritative application boundary for:

- public REST APIs consumed by the React frontend;
- document and processing metadata;
- business validation;
- workflow initiation;
- processing-status queries;
- persistence orchestration;
- internal endpoints used by n8n and Celery;
- health and readiness endpoints.

FastAPI will use:

- Pydantic models for request, response, and configuration validation;
- SQLAlchemy for persistence;
- Alembic for schema migrations;
- generated OpenAPI as the source for the frontend API client;
- dependency injection for database sessions and application services;
- structured logging and explicit exception mapping.

---

# Architectural Boundaries

FastAPI owns business rules and system state.

It must not become a long-running document processor. CPU-intensive and retryable work is delegated to Celery.

The frontend communicates only with FastAPI and does not call n8n, Redis, PostgreSQL, or Celery directly.

n8n may invoke documented internal FastAPI endpoints but must not bypass backend validation by writing application records directly to PostgreSQL.

---

# Rationale

FastAPI is selected because it provides:

- native alignment with the Python OCR and AI ecosystem;
- strong type-driven request and response validation;
- automatic OpenAPI generation;
- asynchronous endpoint support;
- low framework overhead;
- straightforward Docker deployment;
- good compatibility with SQLAlchemy, Alembic, Celery, and Pydantic Settings;
- a compact structure suitable for an MVP without preventing modular growth.

A single Python backend also reduces duplicated domain models and integration code.

---

# Alternatives Considered

## NestJS

Advantages:

- strong TypeScript ecosystem;
- mature modular architecture;
- familiar dependency-injection model;
- shared language with the frontend.

Disadvantages:

- introduces a Node.js-to-Python boundary around OCR and AI processing;
- requires additional internal APIs or duplicated models;
- increases operational and repository complexity for the MVP.

Rejected for the initial implementation.

## Django and Django REST Framework

Advantages:

- mature ecosystem;
- built-in administration and ORM;
- comprehensive conventions.

Disadvantages:

- more framework surface than required;
- less direct fit for a lightweight API and asynchronous processing architecture;
- duplicates the selected SQLAlchemy and Alembic stack.

Rejected for the MVP.

## Flask

Advantages:

- minimal and flexible;
- mature ecosystem.

Disadvantages:

- more manual setup for validation, OpenAPI, dependency management, and application conventions;
- weaker type-driven API development by default.

Rejected.

---

# Consequences

## Positive

- One Python runtime across API, Celery, OCR, and AI integration.
- OpenAPI can generate a typed frontend client.
- Validation rules are explicit and testable.
- Rapid development of internal and public APIs.
- Easier reuse of processing-domain code between API and workers.

## Negative

- Frontend and backend do not share a language.
- Architectural discipline is required to prevent route handlers from accumulating business logic.
- CPU-bound work must be kept outside the API process.
- Async endpoints do not automatically make blocking libraries non-blocking.

---

# Implementation Rules

- Route handlers remain thin.
- Business logic lives in application or service modules.
- Persistence is accessed through explicit repositories or data-access services.
- Pydantic API models are distinct from SQLAlchemy persistence models where their responsibilities differ.
- Database migrations are managed only through Alembic.
- Public endpoints are versioned under `/api`.
- Internal endpoints are isolated and authenticated.
- Errors are returned through a consistent application error schema.
- `/api/health` is available for Phase 0 validation.
- OpenAPI generation is treated as a build contract for `packages/api-client`.

---

# Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Blocking OCR or LLM calls degrade API responsiveness | Execute heavy work in Celery |
| Route layer becomes tightly coupled to persistence | Use service and repository boundaries |
| OpenAPI and frontend client drift | Generate and validate the client in CI |
| Internal endpoints are exposed unintentionally | Separate route namespace and require internal authentication |
| Async code is mixed incorrectly with synchronous DB operations | Establish one documented SQLAlchemy execution model |

---

# Acceptance Criteria

- FastAPI starts through Docker Compose.
- `GET /api/health` returns a successful response.
- Pydantic Settings loads documented environment variables.
- SQLAlchemy connects to PostgreSQL.
- Alembic migrations run successfully.
- OpenAPI is available and can generate the frontend API client.
- Structured errors and logging are configured.
- A protected internal API boundary is defined.
- CPU-intensive processing is delegated to Celery.

---

# Related Documents

- [[../MOC]]
- [[../prd/PRD-Phase-0-Foundation]]
- [[ADR-001-Monorepo]]
- [[ADR-002-Docker-Compose]]
- [[ADR-003-Repository-Structure]]
- [[ADR-006-PostgreSQL]]
- [[ADR-008-Celery]]
- [[ADR-009-n8n]]

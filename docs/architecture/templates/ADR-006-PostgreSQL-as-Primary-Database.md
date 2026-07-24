# ADR-006 — PostgreSQL as the Primary Database

- **Status:** Accepted
- **Date:** 2026-07-24
- **Decision Makers:** Project Team

---

# Context

The Contract Review MVP must persist:

- document metadata;
- processing jobs and status transitions;
- OCR output and confidence data;
- AI extraction results;
- review state and user corrections;
- audit-oriented timestamps and versions;
- n8n runtime state.

The data model contains strong relationships and requires transactional consistency. The system must also support structured JSON payloads for evolving extraction schemas without making all application data schemaless.

Phase 0 requires a database that works reliably in Docker Compose and integrates with FastAPI, SQLAlchemy, Alembic, Celery, and n8n.

---

# Decision

Use **PostgreSQL** as the primary relational database.

PostgreSQL stores authoritative application metadata and structured processing results. SQLAlchemy is the backend persistence layer, and Alembic manages application schema migrations.

The Docker Compose environment may run one PostgreSQL server, but application data and n8n data must be isolated through separate databases or equivalent dedicated schemas and credentials.

PostgreSQL does not store original PDF binaries. Original documents and generated binary artifacts remain in shared file storage during the MVP and may move to object storage later.

---

# Data Ownership

FastAPI and Celery access application tables through the backend persistence layer.

n8n uses its own PostgreSQL database for n8n-managed runtime state.

n8n workflows must not directly modify application-owned tables. They interact with application state through authenticated FastAPI endpoints.

Redis is not an authoritative persistence layer.

---

# Rationale

PostgreSQL provides:

- ACID transactions;
- relational integrity;
- mature indexing and query planning;
- JSONB for flexible extraction payloads;
- broad support from SQLAlchemy, Alembic, Celery-adjacent tooling, and n8n;
- reliable Docker images and local persistence;
- a clear migration path to managed cloud database services;
- support for future full-text and vector extensions if required.

The combination of relational columns and JSONB fits document-processing metadata better than a purely relational or purely document-oriented model.

---

# Storage Strategy

Use relational columns for stable, queryable fields such as:

- identifiers;
- foreign keys;
- document status;
- processing stage;
- timestamps;
- version numbers;
- confidence summaries;
- review state.

Use JSONB selectively for:

- provider-specific metadata;
- evolving extraction payloads;
- structured model output;
- diagnostic details that do not yet justify dedicated tables.

Large files must be referenced by storage path or object key.

---

# Migration Strategy

- Alembic is the only mechanism for application schema evolution.
- Migrations are committed to the repository.
- Startup and CI processes verify the migration state.
- Destructive changes require an explicit data-migration and rollback strategy.
- n8n manages its own schema lifecycle and must not share Alembic migrations.

---

# Alternatives Considered

## SQLite

Advantages:

- minimal setup;
- suitable for simple prototypes.

Disadvantages:

- weaker concurrency characteristics;
- poor fit for multiple containers and workers;
- does not represent the intended production topology.

Rejected.

## MongoDB

Advantages:

- flexible document model;
- convenient storage for variable JSON structures.

Disadvantages:

- core entities and lifecycle records are strongly relational;
- transactional relationships and constraints are important;
- n8n and the selected backend stack already fit PostgreSQL well.

Rejected.

## Separate databases for every service from Phase 0

Advantages:

- stronger isolation;
- closer to a distributed production architecture.

Disadvantages:

- unnecessary local complexity;
- more operational overhead for a single-team MVP.

Deferred. Logical isolation inside one PostgreSQL service is sufficient initially.

---

# Consequences

## Positive

- Strong consistency for processing and review state.
- Explicit relationships and constraints.
- Flexible JSONB support.
- One database technology supports both the application and n8n.
- Straightforward backups and migration to managed PostgreSQL.

## Negative

- Schema and migration discipline are required.
- JSONB can become a dumping ground without governance.
- One local PostgreSQL service is a shared operational dependency.
- Database connections must be sized for API, workers, and n8n.

---

# Operational Requirements

- Use a named Docker volume for persistent data.
- Configure a PostgreSQL health check.
- Use separate credentials for application and n8n access.
- Do not expose PostgreSQL publicly outside the development host unless required.
- Document backup and restore procedures before production deployment.
- Log migration failures clearly.
- Configure connection pooling appropriate to the local environment.
- Never commit database passwords.

---

# Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Application and n8n tables interfere | Separate databases or schemas and credentials |
| JSONB becomes unstructured technical debt | Define stable fields relationally and document JSON schemas |
| Large binaries bloat the database | Store files externally and persist references |
| Concurrent workers overwrite state | Use transactions, constraints, and optimistic locking where needed |
| Migration failure blocks startup | Validate migrations in CI and document recovery |

---

# Acceptance Criteria

- PostgreSQL starts through Docker Compose.
- Persistent data survives container restarts.
- The backend connects through SQLAlchemy.
- Initial Alembic migration executes successfully.
- Application and n8n persistence are logically isolated.
- n8n persists its state in PostgreSQL.
- Original document binaries are stored outside PostgreSQL.
- Database credentials and connection variables are documented in `.env.example`.

---

# Related Documents

- [[../MOC]]
- [[../prd/PRD-Phase-0-Foundation]]
- [[ADR-002-Docker-Compose]]
- [[ADR-004-FastAPI]]
- [[ADR-007-Redis]]
- [[ADR-008-Celery]]
- [[ADR-009-n8n]]

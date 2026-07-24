# ADR-009 — n8n for Workflow Orchestration

- **Status:** Accepted
- **Date:** 2026-07-24
- **Decision Makers:** Project Team

---

# Context

The Contract Review MVP contains a multi-step document-processing workflow:

```text
Upload
→ Validate
→ Native PDF extraction or OCR
→ Chunk
→ AI extraction
→ Persist results
→ Review
```

The workflow must coordinate FastAPI endpoints, Celery tasks, conditional branches, retries, and status transitions. The team also wants workflow execution to be visible, inspectable, and easy to evolve during MVP development.

n8n is included in the local Docker Compose environment and must persist its own state in PostgreSQL.

---

# Decision

Use **n8n** as the workflow-orchestration layer.

n8n coordinates long-running document-processing workflows and external integrations. It does not own application business rules or perform heavy OCR and AI processing directly.

Workflow definitions are exported to version-controlled JSON files under:

```text
n8n/workflows/
```

n8n persists its runtime configuration and execution state in a dedicated PostgreSQL database or schema.

---

# Responsibility Boundaries

## n8n owns

- workflow sequencing;
- conditional branching;
- invocation of authenticated FastAPI internal endpoints;
- initiation or observation of Celery-backed processing steps;
- workflow-level retries and escalation;
- integration with future email, webhook, or external systems;
- execution visibility.

## FastAPI owns

- public and internal API contracts;
- business validation;
- authorization;
- authoritative processing state;
- document and review lifecycle rules;
- database writes to application-owned tables.

## Celery owns

- CPU-intensive and long-running Python work;
- OCR, PDF, chunking, and AI tasks;
- task-level retries;
- processing implementation.

n8n must not directly write application business records to PostgreSQL.

---

# Interaction Pattern

The preferred interaction is:

```text
Frontend
   ↓
FastAPI
   ↓ starts workflow
n8n
   ↓ calls authenticated internal API
FastAPI
   ↓ enqueues task
Celery
   ↓ updates durable state
PostgreSQL
```

Where asynchronous completion cannot be handled in one request, n8n may poll a documented status endpoint or receive a callback through an authenticated endpoint.

Direct n8n-to-Celery broker manipulation is discouraged because it bypasses backend validation and stable task contracts.

---

# Rationale

n8n is selected because it provides:

- visible workflow definitions;
- rapid iteration during MVP development;
- built-in HTTP and integration nodes;
- execution history and debugging;
- conditional branching and retry controls;
- Docker deployment;
- PostgreSQL persistence;
- a practical boundary between orchestration and processing code.

It is particularly useful for future integrations such as email ingestion, notifications, cloud storage, and approval workflows.

---

# Workflow-as-Code Rules

Although n8n is edited visually, exported workflow JSON is treated as source code.

Required practices:

- commit workflow exports under `n8n/workflows/`;
- use stable workflow names and identifiers where practical;
- review workflow changes through pull requests;
- exclude real credentials from exports;
- document required credentials and environment variables;
- avoid environment-specific hostnames in committed workflows;
- test import and activation in a clean local environment;
- update `docs/MOC.md` when a major workflow is added.

The n8n database is runtime state, not the only source of workflow definitions.

---

# Security

- n8n internal endpoints require authentication.
- Credentials are supplied through environment configuration or n8n credential storage.
- No production secrets are committed in workflow JSON.
- n8n is not exposed publicly by default.
- Webhooks must validate authenticity and input.
- Least-privilege database credentials are used.
- n8n cannot directly access application-owned database tables.

---

# Alternatives Considered

## Implement orchestration entirely in FastAPI and Celery

Advantages:

- everything is code-reviewed Python;
- fewer infrastructure services;
- strong testability.

Disadvantages:

- orchestration becomes embedded in application code;
- lower workflow visibility;
- external integrations require more custom implementation;
- slower iteration during the MVP.

Rejected for the initial workflow layer.

## Temporal

Advantages:

- durable execution model;
- strong workflow semantics;
- excellent support for long-running workflows.

Disadvantages:

- significantly greater operational and conceptual complexity;
- excessive for the current MVP scope.

Deferred as a future option if workflow guarantees become more demanding.

## Celery Canvas only

Advantages:

- no additional orchestrator;
- native Python task composition.

Disadvantages:

- limited business-facing visibility;
- workflow logic becomes coupled to task implementation;
- external integrations are less convenient.

Rejected as the primary orchestration mechanism.

---

# Consequences

## Positive

- Processing workflows are visible and inspectable.
- Integrations can be added quickly.
- Orchestration remains separate from business and processing implementation.
- Execution history improves local troubleshooting.
- Workflow assets are version controlled.

## Negative

- Another service must be secured, upgraded, and monitored.
- Visual workflows can become difficult to review as raw JSON.
- State can drift between the n8n database and exported files.
- Poorly designed workflows can duplicate backend business logic.
- Licensing and deployment constraints must be reviewed before production use.

---

# Failure and Retry Model

Retry responsibility is divided by level:

- **Celery** retries bounded task-execution failures.
- **n8n** retries or redirects workflow-step failures.
- **FastAPI/PostgreSQL** records authoritative state and prevents invalid transitions.

Workflows must be idempotent. Repeated callbacks or step execution must not create duplicate documents, jobs, or extraction records.

Terminal failures must be visible through the backend API.

---

# Operational Requirements

- n8n starts through Docker Compose.
- n8n uses PostgreSQL rather than SQLite.
- n8n data survives container restarts.
- A health check or readiness probe is configured.
- Workflow execution logs are available.
- Production execution-data retention is configured deliberately.
- Credentials are not stored in Git.
- Export and import procedures are documented.
- Workflow activation is explicit per environment.

---

# Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Workflow database and Git exports drift | Establish export/import checks and review discipline |
| Business logic leaks into workflows | Keep validation and state transitions in FastAPI |
| Heavy code runs inside n8n | Delegate processing to Celery |
| Duplicate workflow execution | Use idempotency keys and persisted state checks |
| Credentials leak through exports | Use credential references and inspect exported JSON |
| n8n becomes a public attack surface | Keep it internal and secure webhook/API access |

---

# Acceptance Criteria

- n8n starts through Docker Compose.
- n8n is reachable in the local environment.
- n8n persists state in PostgreSQL.
- A Phase 0 test workflow can call an authenticated FastAPI internal endpoint.
- A workflow export is committed under `n8n/workflows/`.
- No real credentials appear in the exported workflow.
- n8n does not directly modify application-owned PostgreSQL tables.
- Responsibilities between n8n, FastAPI, and Celery are documented.
- Workflow state survives container restart.

---

# Related Documents

- [[../MOC]]
- [[../prd/PRD-Phase-0-Foundation]]
- [[ADR-002-Docker-Compose]]
- [[ADR-004-FastAPI]]
- [[ADR-006-PostgreSQL]]
- [[ADR-007-Redis]]
- [[ADR-008-Celery]]

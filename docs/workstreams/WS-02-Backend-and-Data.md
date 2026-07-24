# WS-02 — Backend and Data

**Status:** Accepted
**Date:** 2026-07-24
**Owner:** Backend Team

---

# Purpose

Own the FastAPI application, the persistence layer, and every business rule and authoritative state transition in the system. This is the single seam through which WS-01 (frontend), WS-03 (OCR/AI processing), and WS-04 (n8n) integrate — none of them integrate with each other directly.

---

# Scope

- `apps/backend/app/` — FastAPI application (ADR-004).
- SQLAlchemy models, Alembic migrations, PostgreSQL schema (ADR-006).
- Public REST API (`/api/...`) and internal, authenticated API (`/api/internal/...`) for n8n/Celery.
- Document, OCR-result, extraction, review-state, and audit-log persistence.
- Review state machine (ADR-014) and audit logging (ADR-015).
- OpenAPI generation as the contract for `packages/api-client` and for n8n's internal HTTP calls.
- Redis usage boundaries: cache, idempotency keys, Celery broker/result backend (ADR-007) — Redis itself is provisioned by WS-05, but its usage contracts are defined here.

---

# Responsibilities

- Be the only writer of application-owned PostgreSQL tables (ADR-006, ADR-009 — n8n must not write directly).
- Validate all state transitions (review lifecycle, processing status) server-side.
- Expose stable internal endpoints that WS-04 (n8n) calls to trigger/observe processing steps.
- Expose task-input identifiers (not binaries) for WS-03's Celery tasks to consume, and persist their durable outcomes.
- Keep route handlers thin; business logic lives in services/repositories (ADR-004).
- Version and never silently break the OpenAPI contract that WS-01 depends on.

---

# Out of Scope

- Rendering UI (WS-01).
- Executing OCR, chunking, or LLM inference (WS-03) — the backend enqueues and persists results, it does not perform the compute itself.
- Visual workflow sequencing (WS-04).
- Docker/network/volume provisioning (WS-05), though it consumes what WS-05 provisions.

---

# Deliverables

- `/api/health`, config/logging modules, internal auth middleware (Phase 0).
- Upload endpoint, document schema, workflow-trigger endpoint, status API (Phase 1).
- OCR metadata API, OCR result persistence (Phase 2).
- AI extraction API, prompt/model version tracking (Phase 3).
- Review API (save draft, approve, validation), audit-history API (Phase 4).
- Search API, chat API, retrieval service (Phase 5).

---

# Dependencies

- **Depends on WS-05**: PostgreSQL, Redis, and network topology must exist and be reachable (Compose service names, not `localhost`).
- **Depends on WS-03 contracts**: task names/payload shapes for OCR and AI extraction jobs must be agreed so the backend can enqueue and later persist their results — but WS-02 does not need WS-03's implementation to be finished, only the contract.
- **Depended on by WS-01, WS-03, WS-04**: all three build against this workstream's OpenAPI/internal-API contract.

---

# Consumes

- Compose-provisioned PostgreSQL and Redis connection strings (WS-05).
- Celery task *contracts* (names, payload schema, result schema) from WS-03 — not its internal implementation.
- Workflow trigger calls from n8n (WS-04) against internal endpoints.

# Produces

- OpenAPI spec + generated client consumed by WS-01.
- Internal authenticated API consumed by WS-04 (n8n) to sequence steps.
- Durable job/document/review/audit records that WS-03 tasks read identifiers from and write outcomes back into (via backend endpoints, not direct DB writes).

---

# Milestones by Phase

| Phase | Milestone |
|---|---|
| 0 | Health endpoint, Pydantic settings, SQLAlchemy + Alembic wired, internal auth. |
| 1 | Document upload, metadata persistence, workflow-trigger endpoint, status API. |
| 2 | OCR result persistence and metadata API (ADR-011). |
| 3 | Extraction API, schema validation, confidence + prompt-version storage. |
| 4 | Review API, review state machine (ADR-014), audit log (ADR-015). |
| 5 | Search/chat API backed by pgvector + hybrid retrieval. |

---

# Done Criteria

- OpenAPI is generated and versioned; CI detects contract drift for `packages/api-client`.
- All destructive/critical transitions pass through the review state machine — no boolean flags.
- Every mutation is captured in the append-only audit log.
- No n8n or frontend code path writes directly to application tables.
- Alembic is the only mechanism for schema change.

---

# Risks

| Risk | Mitigation |
|---|---|
| Route handlers accumulate business logic | Enforce service/repository boundaries in review. |
| OpenAPI/frontend client drift | CI generates and diffs the client. |
| Blocking OCR/LLM calls degrade API responsiveness | All heavy work delegated to WS-03 Celery tasks. |
| Concurrent review edits | Optimistic locking / version checks (ADR-014). |

---

# Future Evolution

- Split internal vs. public API into separate routers/auth scopes if complexity grows.
- Introduce dedicated read models for search/chat if hybrid retrieval load grows (ADR-019/ADR-020).

---

# Related Documents

- [[README]]
- [[../MOC]]
- [[../templates/ADR-004-FastAPI-as-Backend-Framework]]
- [[../templates/ADR-006-PostgreSQL-as-Primary-Database]]
- [[../templates/ADR-007-Redis-as-Cache-and-Message-Broker]]
- [[../templates/ADR-014-Review-State-Management]]
- [[../templates/ADR-015-Audit-Logging-Strategy]]
- [[../templates/PRD-Phase-1-Document-Ingestion]]
- [[../templates/PRD-Phase-4-Contract-Review-UI]]

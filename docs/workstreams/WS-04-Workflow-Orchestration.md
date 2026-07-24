# WS-04 — n8n Workflow Orchestration

**Status:** Accepted
**Date:** 2026-07-24
**Owner:** Platform/Integration Team

---

# Purpose

Own the visible, cross-step sequencing of the document-processing pipeline (upload → OCR → chunk → extraction → review; later, RAG retrieval). n8n coordinates *when* things happen; it never implements business rules or heavy processing itself.

---

# Scope

- `n8n/workflows/` — version-controlled workflow JSON exports (ADR-009).
- Upload workflow, OCR workflow, extraction workflow, approval workflow, RAG workflow.
- Conditional branching, workflow-level retries/escalation.
- Calls to WS-02's authenticated internal API endpoints.
- Future external integrations (email ingestion, notifications, cloud storage).

---

# Responsibilities

- Sequence steps by calling WS-02's internal API — never write application tables directly, never manipulate the Celery broker directly (ADR-009).
- Keep workflows idempotent: repeated callbacks/executions must not create duplicate documents, jobs, or extraction records.
- Export every workflow change to `n8n/workflows/` and treat it as reviewed source code.
- Document required credentials/environment variables without committing real secrets.
- Poll or receive authenticated callbacks for steps that can't complete within one request.

---

# Out of Scope

- Business validation, authoritative state, database writes (WS-02).
- OCR/AI/chunking implementation (WS-03).
- UI (WS-01).
- n8n container/database provisioning mechanics (WS-05 provisions the service; this workstream owns what runs inside it).

---

# Deliverables

- Workflow engine running in Compose, persisting to PostgreSQL (Phase 0).
- Upload workflow: triggered on upload, calls internal API (Phase 1).
- OCR workflow: triggers OCR task via backend, observes completion (Phase 2).
- Extraction workflow: triggers AI extraction, handles retries/fallback (Phase 3).
- Approval workflow support: notifies/updates on review-state transitions (Phase 4).
- RAG orchestration workflow: query → retrieval → reranking → prompt construction → LLM → citations → response (ADR-020, Phase 5).

---

# Dependencies

- **Depends on WS-05**: n8n container, PostgreSQL database/schema for n8n runtime state, network reachability to the backend.
- **Depends on WS-02**: internal API endpoints must exist (as a contract) for each workflow step it needs to call.
- **Does not depend on WS-03 directly** — it triggers/observes WS-03's work exclusively through WS-02's internal API, which is what keeps this workstream decoupled from Celery task implementation details.

---

# Consumes

- WS-02's internal, authenticated API endpoints (trigger, status, callback).
- WS-05-provisioned PostgreSQL database (its own, isolated from application tables) and network topology.

# Produces

- Version-controlled workflow definitions (`n8n/workflows/*.json`) that document the pipeline's actual sequencing — the reference for anyone debugging "what happens after upload."
- Execution history/logs useful to WS-06 for tracing processing failures.

---

# Milestones by Phase

| Phase | Milestone |
|---|---|
| 0 | n8n starts, persists to PostgreSQL, a test workflow calls an authenticated internal endpoint. |
| 1 | Upload workflow triggers automatically and is idempotent. |
| 2 | OCR workflow observes/handles OCR completion and failure. |
| 3 | Extraction workflow with retry/escalation. |
| 4 | Approval-related workflow support (notifications, status propagation). |
| 5 | RAG orchestration workflow (ADR-020). |

---

# Done Criteria

- No workflow writes directly to application-owned PostgreSQL tables.
- No workflow manipulates the Celery broker directly.
- Every workflow is idempotent under retry/duplicate execution.
- Every workflow change is exported and committed; no drift between the n8n runtime and the committed JSON.
- No real credentials appear in exported workflow JSON.

---

# Risks

| Risk | Mitigation |
|---|---|
| Workflow DB and Git exports drift | Export/import checks, review discipline. |
| Business logic leaks into workflows | Keep validation/state transitions in WS-02; code review catches drift. |
| Duplicate workflow execution | Idempotency keys, persisted state checks in WS-02. |
| Credentials leak through exports | Use credential references; inspect exported JSON before commit. |
| n8n becomes a public attack surface | Keep internal-only; secure webhook/API access. |

---

# Future Evolution

- Consider Temporal if durable-execution guarantees outgrow n8n (ADR-009 notes this as deferred, not rejected).
- Add email ingestion, external notifications, and cloud-storage integrations as they become required.

---

# Related Documents

- [[README]]
- [[../MOC]]
- [[../templates/ADR-009-n8n-for-Workflow-Orchestration]]
- [[../templates/ADR-020-RAG-Orchestration]]
- [[../templates/PRD-Phase-1-Document-Ingestion]]

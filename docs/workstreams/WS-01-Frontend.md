# WS-01 — Frontend

**Status:** Accepted
**Date:** 2026-07-24
**Owner:** Frontend Team

---

# Purpose

Own every browser-facing surface of the Contract Review MVP: application shell, upload experience, processing-status visibility, OCR/extraction viewers, the review workspace, and eventual search/chat UI. Deliver a typed, componentized React application that talks to exactly one backend: FastAPI.

---

# Scope

- `apps/frontend/` — React + TypeScript + Vite application (ADR-005).
- Application shell: routing, layout, error boundary, theming (Material UI).
- Server-state management via TanStack Query.
- Document list, upload flow, processing-status indicators.
- PDF viewer, OCR text viewer, extracted-fields panel, field editing, confidence indicators, validation error display (PRD-4).
- Approval workflow UI, audit-history display.
- Search and conversational Q&A UI (PRD-5), with citations.
- Consumption of the generated API client (`packages/api-client`).

---

# Responsibilities

- Implement UI strictly against the OpenAPI contract published by WS-02.
- Keep all authoritative business/validation logic out of the frontend; UI-side validation is for usability only (ADR-005).
- Maintain accessibility, responsiveness, and autosave UX for the review workspace (PRD-4 NFRs).
- Handle large documents via pagination/virtualization/lazy loading.
- Report bugs against the API contract (not against WS-02's internals) so backend and frontend can iterate independently.

---

# Out of Scope

- Business logic, persistence, or authoritative state (owned by WS-02).
- OCR, chunking, or AI extraction execution (owned by WS-03).
- Workflow orchestration (owned by WS-04).
- Infrastructure, Docker, deployment topology (owned by WS-05).
- Authentication/authorization (explicitly out of scope for the MVP per every phase PRD).

---

# Deliverables

- React application shell (Phase 0).
- Upload UI with drag-and-drop and progress (Phase 1).
- Document list, status polling/viewer (Phase 1–2).
- OCR text viewer synchronized with PDF viewer (Phase 2).
- Extraction editor with confidence indicators and validation errors (Phase 3–4).
- Review dashboard and approval workflow (Phase 4).
- Search and chat UI with citations (Phase 5).

---

# Dependencies

- **Depends on WS-02**: OpenAPI contract and the generated client in `packages/api-client`. Frontend work on any feature cannot start rendering real data until the corresponding endpoint contract exists (a mocked contract is sufficient — the real implementation is not required).
- **Depends on WS-05**: Compose service is reachable (`VITE_API_BASE_URL`) and the frontend container builds/runs.
- Does **not** depend on WS-03 or WS-04 directly — those are opaque to the frontend, surfaced only through WS-02 API responses (status fields, extracted JSON, audit entries).

---

# Consumes

- OpenAPI spec + generated TypeScript client from `packages/api-client` (WS-02).
- Document, OCR, extraction, review, and audit REST resources (WS-02).
- Search/chat endpoints with citation payloads (WS-02, Phase 5).

# Produces

- No downstream technical consumers; this workstream is a leaf. Its "producer" role is UX feedback that shapes API design (e.g., requesting fields, pagination shape, error schema) back to WS-02.

---

# Milestones by Phase

| Phase | Milestone |
|---|---|
| 0 | Shell renders, health check call succeeds, error boundary present. |
| 1 | Upload with progress; document list with live status. |
| 2 | OCR viewer synced to PDF; confidence indicators visible. |
| 3 | Extraction fields rendered from structured JSON; validation errors surfaced. |
| 4 | Full review workspace: edit, save draft, approve, audit trail visible. |
| 5 | Search UI, semantic/hybrid results, chat with citations. |

---

# Done Criteria

- Strict TypeScript checks pass.
- No direct calls to Postgres/Redis/n8n/Celery from frontend code.
- All server state goes through TanStack Query; no ad hoc `fetch`.
- Top-level error boundary catches unrecoverable render failures.
- API client is generated, not hand-written, and CI flags contract drift.

---

# Risks

| Risk | Mitigation |
|---|---|
| Backend API not ready when frontend needs it | Build against OpenAPI mock/generated client first; don't block on live implementation. |
| API types drift from backend models | CI regenerates and diffs the client from OpenAPI. |
| Large documents cause rendering problems | Virtualization, pagination, incremental loading. |
| Review UI accumulates business logic | Route logic decisions back to WS-02; frontend stays a thin, typed consumer. |

---

# Future Evolution

- Introduce a global client-state library only if a concrete cross-cutting need emerges (ADR-005 already defers this).
- Add real-time status via WebSocket/SSE instead of polling, once backend supports it.
- Multi-tenant/auth-aware views once auth lands (post-MVP).

---

# Related Documents

- [[README]]
- [[../MOC]]
- [[../templates/ADR-005-React-TypeScript-Vite]]
- [[../templates/ADR-014-Review-State-Management]]
- [[../templates/PRD-Phase-4-Contract-Review-UI]]
- [[../templates/PRD-Phase-5-Search-and-Knowledge-Base-RAG]]

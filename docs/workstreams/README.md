# Workstreams — Parallel Execution Model

**Status:** Accepted
**Date:** 2026-07-24
**Owner:** Engineering

---

# Purpose

Phases (`docs/architecture/templates/PRD-Phase-*`) define **what** ships and **when**. Workstreams define **who owns which surface** and **how work is parallelized without teams blocking each other**.

A phase is a vertical slice delivered by several workstreams working concurrently. A workstream is a horizontal, persistent area of ownership that spans every phase.

---

# The Six Workstreams

| ID | Name | Doc |
|----|------|-----|
| WS-01 | Frontend | [[WS-01-Frontend]] |
| WS-02 | Backend and Data | [[WS-02-Backend-and-Data]] |
| WS-03 | Document Processing and OCR | [[WS-03-Document-Processing-and-OCR]] |
| WS-04 | n8n Workflow Orchestration | [[WS-04-Workflow-Orchestration]] |
| WS-05 | Infrastructure and DevOps | [[WS-05-Infrastructure-and-DevOps]] |
| WS-06 | Quality, Testing, and Documentation | [[WS-06-Quality-Testing-and-Documentation]] |

---

# Dependency Graph

```text
                 WS-06 (Quality, cross-cutting — reviews everything)
                    ▲
                    │
   WS-01 ───────► WS-02 ◄─────── WS-03
 (Frontend)     (Backend/Data)  (OCR/AI Processing)
                    ▲
                    │
                  WS-04
                  (n8n)
                    │
                    ▼
                  WS-05
              (Infrastructure)
```

- **WS-05** is the foundation: everything else runs inside the containers, network, and volumes it defines.
- **WS-02** is the hub: it is the *only* system of record. WS-01, WS-03, and WS-04 all depend on its API contract, but never on each other directly.
- **WS-01** and **WS-03** never call each other. They meet only through WS-02's API.
- **WS-04** sequences work by calling WS-02's internal endpoints; it does not call WS-03 directly.
- **WS-06** is cross-cutting: it does not block any workstream's implementation, but it gates merges (CI, tests, ADR/PRD upkeep).

This shape is intentional: **WS-02's OpenAPI contract is the seam** that lets WS-01, WS-03, and WS-04 build in parallel against a stable interface instead of each other's in-progress code.

---

# Mapping to Phases

| Workstream | Phase 0 | Phase 1 | Phase 2 | Phase 3 | Phase 4 | Phase 5 |
|---|---|---|---|---|---|---|
| WS-01 Frontend | Application shell | Upload UI | Status/OCR viewer | Extraction viewer | Review UI | Search & chat UI |
| WS-02 Backend/Data | API foundation | Upload API, document schema | OCR metadata API | Extraction API, review-state schema | Review API, audit log | Search/chat API |
| WS-03 OCR/AI Processing | Celery scaffold | File validation task | OCR pipeline | AI extraction, prompt mgmt | — | Chunking, embeddings |
| WS-04 n8n | Workflow engine | Upload workflow | OCR workflow | Extraction workflow | Approval workflow | RAG workflow |
| WS-05 Infrastructure | Docker stack, `.env` | Shared storage volume | OCR engine container | Model/provider config | — | Vector DB (pgvector) |
| WS-06 Quality | ADRs/PRDs, repo conventions | Ingestion tests | OCR regression fixtures | Extraction schema tests | Review/audit tests | Retrieval eval |

---

# Rules for Parallelism

1. **Contract-first.** WS-02 publishes OpenAPI (and internal endpoint contracts) before WS-01/WS-03/WS-04 build against them. Breaking changes require a heads-up in the PR, not a hallway conversation.
2. **No lateral dependencies.** WS-01 and WS-03 integrate only through WS-02. n8n (WS-04) integrates only through WS-02's internal API, never the Celery broker or Postgres directly (per ADR-009).
3. **Mock the seam, not the neighbor.** Frontend developers use a mocked/generated API client against the OpenAPI spec; they don't wait for the real backend endpoint to exist. Backend developers stub OCR/AI task results to build the Review API before WS-03's pipeline is done.
4. **Every workstream owns its own tests.** Cross-workstream integration tests live under WS-06 and run in CI, not in a shared branch.
5. **Infrastructure changes are additive during a phase.** WS-05 adds services/volumes/env vars; it does not restructure Compose topology mid-phase without notifying all workstreams (this is itself a mini-ADR if structural).
6. **Documentation is not optional overhead.** Each workstream keeps its own doc's `Consumes`/`Produces` sections current — that's what makes the seams visible to everyone else.

---

# Related Documents

- [[../MOC]]
- [[../Progress]]
- [[../templates/ADR-001-Monorepo]]
- [[../templates/ADR-003-Repository-Structure]]
- [[../templates/ADR-009-n8n-for-Workflow-Orchestration]]

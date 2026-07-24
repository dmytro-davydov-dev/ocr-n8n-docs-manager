# WS-03 — Document Processing and OCR

**Status:** Accepted
**Date:** 2026-07-24
**Owner:** Processing/AI Team

---

# Purpose

Own all CPU-intensive and AI-driven document processing: PDF handling, OCR, chunking, AI extraction, prompt management, and embeddings. This workstream implements the Celery task layer and never exposes itself directly to the frontend or n8n — only through the contracts published by WS-02.

---

# Scope

- Celery worker (`apps/backend/`, worker entrypoint) — background task execution (ADR-008).
- PDF rasterization and native text extraction.
- OCR via PaddleOCR behind an internal OCR service (ADR-010); OCR result persistence strategy (ADR-011, implemented as WS-02 tables, populated by this workstream's tasks).
- AI extraction via a provider-agnostic LLM abstraction (ADR-012).
- Prompt versioning and management (ADR-013).
- Document chunking strategy for RAG (ADR-018).
- Embedding generation via a provider-agnostic embedding abstraction (ADR-017).

---

# Responsibilities

- Implement tasks that accept identifiers/small metadata (never binaries) and load input from shared storage.
- Guarantee idempotency under Celery's at-least-once delivery (ADR-008).
- Distinguish retryable failures (transient/provider) from terminal ones (invalid input).
- Persist durable outcomes only through WS-02's application services/endpoints — never write application tables directly.
- Record OCR engine version, model name/version, and prompt version with every result for traceability.
- Keep provider selection (OCR engine, LLM, embedding model) swappable via configuration, not code changes.

---

# Out of Scope

- API surface, schema ownership, or review-state transitions (WS-02).
- Deciding *when* a task runs in the broader business workflow — that sequencing lives in WS-04 (n8n); this workstream only executes the unit of work once triggered.
- UI (WS-01).
- Container/network provisioning, though it runs inside containers WS-05 defines.

---

# Deliverables

- Celery app scaffold, Redis broker wiring (Phase 0).
- File validation/inspection task (Phase 1).
- OCR pipeline: rasterization, PaddleOCR invocation, confidence scoring, retry support (Phase 2).
- AI extraction: prompt templates, structured JSON output, validation, retry/fallback (Phase 3).
- Chunking pipeline with configurable token limits/overlap and chunk metadata (Phase 5).
- Embedding generation pipeline with model/version tagging (Phase 5).

---

# Dependencies

- **Depends on WS-05**: worker container, Redis broker, shared document storage volume must exist.
- **Depends on WS-02**: durable persistence goes through backend services; this workstream needs the contract (task payload/result schema) agreed with WS-02, not the finished backend implementation.
- **Depended on by WS-04**: n8n triggers/observes these tasks indirectly via WS-02's internal API — WS-03 has no direct relationship with n8n.

---

# Consumes

- Task trigger + input identifiers via Celery messages (routed from WS-02, sequenced by WS-04).
- Shared document storage paths (WS-05).
- Provider credentials/config for OCR, LLM, and embedding backends (WS-05 environment configuration).

# Produces

- OCR text, confidence scores, and page-level metadata — persisted via WS-02 endpoints/services.
- Structured extraction JSON with confidence and prompt/model version — persisted via WS-02.
- Chunks with page/section/offset metadata and embeddings — persisted via WS-02 (pgvector, ADR-016).

---

# Milestones by Phase

| Phase | Milestone |
|---|---|
| 0 | Celery worker starts, connects to Redis, executes a test task. |
| 1 | File validation task runs on upload. |
| 2 | Full OCR pipeline: multi-page processing, confidence, retries. |
| 3 | AI extraction pipeline: schema validation, confidence, prompt/model versioning. |
| 5 | Chunking + embedding pipeline feeding pgvector. |

---

# Done Criteria

- All tasks are safe to retry (idempotent) and tolerate duplicate delivery.
- Task payloads contain identifiers only — never file binaries or secrets.
- Every task records enough version/context to reproduce or debug a result without re-running it blind.
- OCR engine, LLM provider, and embedding model are all swappable via configuration.

---

# Risks

| Risk | Mitigation |
|---|---|
| LLM hallucinations | Schema validation, confidence thresholds (PRD-3). |
| OCR/LLM provider outages | Retry with backoff; provider abstraction allows failover. |
| Prompt regressions | Versioned prompts + regression tests (ADR-013). |
| CPU/memory exhaustion from OCR | Dedicated queue, controlled concurrency (ADR-008). |
| Duplicate task execution | Idempotency keys, deterministic artifact paths. |

---

# Future Evolution

- Split OCR/AI/chunking onto dedicated Celery queues if resource contention appears (ADR-008 already anticipates this).
- Add layout-aware extraction as PaddleOCR capability matures (ADR-010).
- Re-embed/re-index on embedding model upgrades (ADR-017).

---

# Related Documents

- [[README]]
- [[../MOC]]
- [[../templates/ADR-008-Celery-for-Background-Processing]]
- [[../templates/ADR-010-OCR-Engine-Selection]]
- [[../templates/ADR-011-OCR-Storage-Strategy]]
- [[../templates/ADR-012-LLM-Provider-Selection]]
- [[../templates/ADR-013-Prompt-Management-Strategy]]
- [[../templates/ADR-017-Embedding-Model-Strategy]]
- [[../templates/ADR-018-Document-Chunking-Strategy]]
- [[../templates/PRD-Phase-2-OCR-Pipeline]]
- [[../templates/PRD-Phase-3-AI-Extraction]]

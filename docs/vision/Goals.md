# Goals

**Status:** Accepted
**Date:** 2026-07-26
**Owner:** Product & Engineering

---

# 1. Purpose

This document states what the Contract Review [[../Tech-Glossary#MVP|MVP]] must achieve, broken into the north-star goal, the per-phase goals that already exist in each [[../Tech-Glossary#PRD|PRD]], and the cross-cutting engineering goals that apply across every phase. It exists so any [[../Tech-Glossary#Workstream|workstream]] can check its own work against the same bar. See [[Vision]] for why this product exists.

---

# 2. North-Star Goal

A user can upload a scanned contract, watch it move automatically through [[../Tech-Glossary#OCR|OCR]] and [[../Tech-Glossary#AI|AI]] extraction, review and approve the extracted fields with full [[../Tech-Glossary#Audit Log|audit history]], and then find that contract again — and ask a grounded, cited question about it — through search and chat. All of it runs from a single `docker compose up --build`, with no manual setup step beyond providing an [[../Tech-Glossary#LLM|LLM]]/[[../Tech-Glossary#Embedding|embedding]] [[../Tech-Glossary#API|API]] key.

---

# 3. Phase Goals

| Phase | Goal | Exit Criteria |
|---|---|---|
| **0 — Foundation** | A fully reproducible local dev environment: every core service (frontend, backend, [[../Tech-Glossary#PostgreSQL\|Postgres]], [[../Tech-Glossary#Redis\|Redis]], [[../Tech-Glossary#Celery\|Celery]], [[../Tech-Glossary#n8n\|n8n]]) starts and communicates with one command. | Any developer can clone the repo, run `docker compose up --build`, and get a working stack with no manual configuration. |
| **1 — Document Ingestion** | A reliable pipeline from upload to processing start: a user can upload a PDF, have it stored and its metadata persisted, and see an n8n workflow trigger automatically. | A user uploads a document through the frontend; it's stored, recorded, and automatically starts processing with visible status. |
| **2 — OCR Pipeline** | Every uploaded page is reliably converted to text, stored per-page, with the OCR engine chosen purely by configuration. | Documents run through OCR automatically and page-level text/confidence is retrievable via the API. |
| **3 — AI Extraction** | An LLM reliably proposes structured contract fields (parties, dates, monetary values, key clauses, obligations) from OCR text, validated against a schema, with the provider swappable by configuration. | Extraction runs automatically after OCR and produces schema-valid, retrievable structured output, with failures distinguishable from "not yet run." |
| **4 — Contract Review UI** | A reviewer can see the original PDF, OCR text, and extracted fields together, edit and validate fields, and approve or reject — with every action captured in an audit trail. | Users can reliably review, edit, validate, and approve AI-generated contract data with complete traceability. |
| **5 — Search & Knowledge Base ([[../Tech-Glossary#RAG\|RAG]])** | Approved contracts are automatically indexed for keyword and [[../Tech-Glossary#Semantic Search\|semantic search]], and answerable through a chat interface whose answers cite verifiable source passages. | Reviewed contracts are searchable by keyword and meaning, and users get grounded AI answers with verifiable citations. |

---

# 4. Cross-Cutting Engineering Goals

These apply to every phase and every workstream, not just one:

- **[[../Tech-Glossary#Idempotent|Idempotent]], resumable pipelines.** Every processing task (validation, OCR, extraction, embedding) re-checks the document's current state before acting, so retries and re-dispatches are always safe no-ops rather than duplicated work.
- **Provider swappability.** OCR engine, LLM provider, and embedding model are each selected through configuration alone — never a code change — per [[../architecture/templates/ADR-010-OCR-Engine-Selection]], [[../architecture/templates/ADR-012-LLM-Provider-Selection]], and [[../architecture/templates/ADR-017-Embedding-Model-Strategy]].
- **Contract-first parallelism.** WS-02's backend API is the only seam between workstreams (per [[../workstreams/README]]); frontend, OCR/AI processing, and workflow orchestration build against that contract, never against each other's internals.
- **Complete auditability.** Every mutation — upload, OCR run, extraction, review edit, approval, rejection, retry — is written to an append-only audit log, and reviewed data is always kept separate from raw AI output.
- **Traceable AI output.** Extracted fields carry confidence scores and [[../Tech-Glossary#Prompt|prompt]]/model version; chat answers cite the exact document, page, and [[../Tech-Glossary#Chunking|chunk]] they were retrieved from, rather than trusting the model to self-report sources.
- **[[../Tech-Glossary#CI|CI]]-gated quality.** Every workstream owns its own tests; merges are blocked on test failures, migration errors, and OpenAPI contract drift.

---

# 5. Non-Goals

Explicitly out of scope for this set of goals (see [[Vision]] §7 for the full list): end-user authentication/authorization, multi-tenant deployment, analytics/reporting, and email integration.

---

# 6. Related Documents

- [[Vision]]
- [[../Tech-Glossary]]
- [[../MOC]]
- [[../architecture/Progress]]
- [[../workstreams/README]]
- [[../architecture/templates/PRD-Phase-0-Foundation]]
- [[../architecture/templates/PRD-Phase-1-Document-Ingestion]]
- [[../architecture/templates/PRD-Phase-2-OCR-Pipeline]]
- [[../architecture/templates/PRD-Phase-3-AI-Extraction]]
- [[../architecture/templates/PRD-Phase-4-Contract-Review-UI]]
- [[../architecture/templates/PRD-Phase-5-Search-and-Knowledge-Base-RAG]]

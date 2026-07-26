# Vision

**Status:** Accepted
**Date:** 2026-07-26
**Owner:** Product & Engineering

---

# 1. Problem Statement

Contracts arrive as scanned or photographed PDFs, not structured data. Today, getting the parties, dates, monetary values, key clauses, and obligations out of a contract means someone reading it by hand and re-keying what they find into another system. That work is slow, inconsistent between reviewers, and leaves no trace of who changed what or why. Once a contract has been reviewed, it usually disappears into a folder — there is no way to search across a portfolio of contracts or ask a plain-language question ("which vendor contracts renew in Q1?") without re-opening every file.

# 2. Vision Statement

Docs Processor turns a pile of scanned contracts into a reviewed, trustworthy, searchable knowledge base — with a human always in control of what counts as fact.

A user uploads a contract PDF. The platform [[../Tech-Glossary#OCR|OCRs]] it, uses an [[../Tech-Glossary#LLM|LLM]] to propose structured fields (parties, dates, monetary values, key clauses, obligations), and hands that proposal to a reviewer who edits, validates, and approves it — every change recorded in an [[../Tech-Glossary#Audit Log|audit trail]]. Once approved, the contract's content is indexed for keyword and [[../Tech-Glossary#Semantic Search|semantic search]], and can be queried through natural-language chat with answers that cite the exact source passages.

# 3. Target Users

- **Reviewers / paralegals** — the primary users of the Contract Review UI (Phase 4): they check AI-extracted fields against the source document, correct them, and approve or reject.
- **Contract managers / legal ops** — consumers of the search and chat surface (Phase 5): they need to find and reason across a portfolio of already-approved contracts.
- **Engineering** — owns and extends the six workstreams (frontend, backend/data, OCR/AI processing, workflow orchestration, infrastructure, quality) that build and operate the platform itself.

# 4. Product Overview

The product is a single pipeline with a human checkpoint in the middle:

1. **Ingestion** — upload a PDF, store it, record its metadata, trigger processing.
2. **OCR** — extract page-level text from the stored document.
3. **[[../Tech-Glossary#AI|AI]] extraction** — an LLM reads the OCR text and proposes structured contract fields against a versioned schema and prompt.
4. **Review** — a reviewer sees the original PDF, the OCR text, and the extracted fields side by side, edits and validates them, and approves or rejects. Every edit and transition is captured in an append-only audit log.
5. **Search & knowledge base ([[../Tech-Glossary#RAG|RAG]])** — only *approved* contracts are [[../Tech-Glossary#Chunking|chunked]], [[../Tech-Glossary#Embedding|embedded]], and made searchable by keyword and by meaning, with chat answers grounded in citable source passages.

[[../Tech-Glossary#n8n|n8n]] orchestrates the workflow between these steps; the backend ([[../Tech-Glossary#FastAPI|FastAPI]]) is the single system of record and the only integration seam between them, so the frontend, the OCR/AI processing layer, and the workflow engine can all be built and changed independently of one another.

# 5. Guiding Principles

- **Human-in-the-loop, always.** AI proposes; a person disposes. Nothing extracted by the model is treated as authoritative until a reviewer approves it, and only approved contracts are searchable.
- **Full traceability.** Every upload, extraction, edit, and status transition is written to an immutable audit log. Reviewed data and original AI output are kept separate so a correction never silently overwrites what the model actually said.
- **Provider independence.** The OCR engine, the LLM provider, and the embedding model are each selected by configuration, not code — a deployment can swap any of them without a code change.
- **Contract-first parallelism.** The backend's [[../Tech-Glossary#API|API]] is the seam between [[../Tech-Glossary#Workstream|workstreams]]. Frontend, OCR/AI processing, and workflow orchestration integrate only through that API and never depend on each other's internals, so they can be built concurrently.
- **Local-first, reproducible.** The entire stack runs from a single `docker compose up --build`, with no required external service for local development.
- **Ship in vertical, provable slices.** Each phase is a working, demonstrable increment (Foundation → Ingestion → OCR → AI Extraction → Review UI → Search & RAG) rather than a big-bang release.

# 6. What Success Looks Like

- A reviewer can upload a scanned contract and, without touching any other tool, watch it move through OCR and AI extraction to a review screen with the original document, OCR text, and extracted fields visible together.
- A reviewer can correct extracted fields, save a draft, and approve — with the full history of edits and approvals available afterward.
- Once approved, that contract's content is searchable by keyword or meaning, and a legal-ops user can ask a natural-language question and get an answer with citations back to the exact page and passage.
- Every one of the above works against a fully local stack started with one command, with OCR engine, LLM provider, and embedding model each swappable purely through configuration.

# 7. Out of Scope for the MVP

- End-user authentication and authorization
- Multi-tenant deployment
- Analytics/reporting beyond the audit log
- Email notifications/integration

These are deliberately deferred so the [[../Tech-Glossary#MVP|MVP]] can prove the core upload → OCR → extract → review → search loop first.

# 8. Related Documents

- [[Goals]]
- [[../Tech-Glossary]]
- [[../MOC]]
- [[../architecture/Progress]]
- [[../workstreams/README]]
- [[../architecture/templates/PRD-Phase-0-Foundation]]
- [[../architecture/templates/PRD-Phase-4-Contract-Review-UI]]
- [[../architecture/templates/PRD-Phase-5-Search-and-Knowledge-Base-RAG]]

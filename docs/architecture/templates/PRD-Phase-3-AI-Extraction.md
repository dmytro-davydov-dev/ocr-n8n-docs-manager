# PRD — Phase 3: AI Extraction

**Version:** 1.0  
**Status:** Draft  
**Owner:** Engineering

---

# 1. Purpose

Phase 3 introduces AI-powered extraction of structured information from OCR text. The system transforms unstructured contract text into normalized business entities using Large Language Models (LLMs) and deterministic validation.

---

# 2. Goals

Automatically extract contract metadata, key clauses, parties, dates, monetary values, and obligations with traceable confidence scores and human-review readiness.

---

# 3. In Scope

## AI Processing

- LLM-based extraction
- Prompt templates
- Structured JSON output
- Confidence scoring
- Validation pipeline
- Retry and fallback strategy

## Backend

- AI extraction jobs
- Extraction API
- Result persistence
- Versioned prompts
- Audit trail

## Infrastructure

- AI worker
- Queue integration
- n8n orchestration
- Secure model configuration

---

# 4. Out of Scope

- Human review interface
- Manual editing
- Search/RAG
- User authentication
- Production model fine-tuning

---

# 5. Functional Requirements

FR-301 OCR completion triggers AI extraction.

FR-302 The LLM returns structured JSON.

FR-303 Extracted entities are validated against a schema.

FR-304 Validation failures are logged.

FR-305 Confidence scores are stored.

FR-306 Prompt version is recorded.

FR-307 Users can retrieve extraction results through the API.

FR-308 Every extraction is traceable to its OCR input and model version.

---

# 6. Non-functional Requirements

- Deterministic output schema
- Idempotent processing
- Prompt versioning
- Full auditability
- Configurable AI providers
- Extensible extraction architecture

---

# 7. Deliverables

- AI extraction service
- Prompt library
- JSON schemas
- Validation engine
- AI workflow in n8n
- Database schema updates
- Backend endpoints

---

# 8. Dependencies

- Phase 0 completed
- Phase 1 completed
- Phase 2 completed

---

# 9. Risks

| Risk | Mitigation |
|------|------------|
| LLM hallucinations | Schema validation and confidence thresholds |
| Provider outages | Retry and provider abstraction |
| Prompt regressions | Prompt versioning and regression tests |
| Low extraction quality | Human review in next phase |

---

# 10. Acceptance Criteria

- OCR output automatically starts AI extraction.
- Structured JSON is generated.
- Validation succeeds for supported document types.
- Confidence scores are persisted.
- Prompt and model versions are recorded.
- Results are available through the backend API.
- Every extraction is fully traceable.

---

# 11. Related ADRs

- ADR-009 — n8n
- ADR-010 — OCR Engine Selection
- ADR-011 — OCR Storage Strategy
- ADR-012 — LLM Provider Selection (future)
- ADR-013 — Prompt Management Strategy (future)

---

# 12. Related Documents

- [[../MOC]]
- [[../architecture/Progress]]
- [[../implementation/High-Level-Implementation-Plan]]

---

# 13. Exit Criteria

Phase 3 is complete when OCR text is automatically transformed into validated structured contract data suitable for human review and downstream business workflows.

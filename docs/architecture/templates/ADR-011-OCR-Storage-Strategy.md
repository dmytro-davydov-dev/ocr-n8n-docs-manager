# ADR-011 — OCR Storage Strategy

**Status:** Accepted  
**Date:** 2026-07-24

# Context

OCR output will be consumed by AI extraction, search, auditing, and future RAG capabilities.

# Decision

Persist OCR results as structured page-level records in PostgreSQL while preserving the original document in object storage/shared volume.

Each OCR result stores:
- document_id
- page_number
- extracted_text
- confidence_score
- processing_timestamp
- OCR engine version

# Rationale

Separating source documents from OCR output allows OCR to be rerun without duplicating files and enables downstream services to consume normalized text.

# Alternatives Considered

- Single text blob
- JSON-only storage
- File-based OCR output

# Consequences

## Positive

- Page-level traceability
- Easy AI processing
- Efficient search indexing
- Supports reprocessing

## Negative

- Additional database storage
- More tables to maintain

## Risks

- Schema evolution as OCR capabilities expand.

# Related Documents

- PRD-Phase-2-OCR-Pipeline
- ADR-006-PostgreSQL

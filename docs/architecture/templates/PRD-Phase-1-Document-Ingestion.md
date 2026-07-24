# PRD — Phase 1: Document Ingestion

**Version:** 1.0
**Status:** Draft
**Owner:** Engineering

---

## 1. Purpose

Phase 1 delivers the first end-to-end business capability: ingesting documents into the platform. Users can upload supported files, which are stored, registered in the database, and trigger an automated processing workflow in n8n. OCR, AI extraction, and review are intentionally deferred to later phases.

## 2. Goals

Provide a reliable pipeline from document upload to processing initiation.

At the end of this phase a user can:

- Upload a PDF through the web UI.
- Persist document metadata.
- Store the original file.
- Trigger an n8n workflow.
- Observe document processing status.

## 3. In Scope

## Frontend

- Upload page
- Drag-and-drop upload
- Upload progress
- Document list
- Processing status
- Error handling

## Backend

- Upload endpoint
- File validation
- Metadata persistence
- Storage abstraction
- Workflow trigger endpoint
- Document status API

## Infrastructure

- Shared storage volume
- n8n webhook integration
- Background processing queue
- Database schema for documents

## 4. Out of Scope

- OCR
- AI extraction
- Clause detection
- Review UI
- Authentication and authorization
- Email notifications

## 5. Functional Requirements

FR-101 Upload PDF documents.

FR-102 Validate supported file types and size.

FR-103 Persist document metadata in PostgreSQL.

FR-104 Store original files in shared storage.

FR-105 Trigger an n8n workflow after successful upload.

FR-106 Track document lifecycle (Uploaded, Queued, Processing, Failed).

FR-107 Return upload and processing status via API.

FR-108 Display document list and current status in the frontend.

## 6. Non-functional Requirements

- Uploads are transactional.
- Files are never modified after upload.
- API responses are structured and versioned.
- Workflow triggering is idempotent.
- Processing failures are logged.
- Components remain independently deployable.

## 7. Deliverables

- Upload UI
- Document API
- Document database model
- Storage service
- n8n upload workflow
- Document status endpoint
- Initial integration tests

## 8. Dependencies

- Phase 0 completed
- Docker infrastructure
- PostgreSQL
- Redis
- n8n

## 9. Risks

| Risk | Mitigation |
| --- | --- |
| Large uploads | File size limits and streaming uploads |
| Duplicate uploads | Content hash and duplicate detection |
| Workflow failures | Retry strategy and status tracking |
| Storage growth | Configurable storage location and retention policy |

## 10. Acceptance Criteria

- User uploads a PDF successfully.
- Metadata is persisted.
- File is stored.
- n8n workflow starts automatically.
- Document status updates correctly.
- Errors are surfaced in the UI.
- Integration tests pass.

## 11. Related ADRs

- [[ADR-001-Monorepo]]
- [[ADR-002-Docker-Compose]]
- ADR-010-Document-Storage (planned)
- ADR-011-Document-Ingestion (planned)
- ADR-012-n8n-Workflow-Orchestration (planned)

## 12. Related Documents

- [[../../MOC]]
- [[../Progress]]
- [[../implementation/High-Level-Implementation-Plan]]
- [[PRD-Phase-0-Foundation]]

## 13. Exit Criteria

Phase 1 is complete when a user can upload a document through the frontend and the platform reliably stores it, records its metadata, and automatically starts the corresponding n8n workflow with visible processing status.

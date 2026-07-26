# Contract Review MVP — Map of Content

## Reference

- [[Tech-Glossary]] — plain-English explanations of [[Tech-Glossary#OCR|OCR]], [[Tech-Glossary#AI|AI]], [[Tech-Glossary#RAG|RAG]], and other terms used throughout this knowledge base, for non-technical readers.

## Vision

- [[vision/Vision]]
- [[vision/Goals]]

## Planning

- [[implementation/High-Level-Implementation-Plan]]
- [[architecture/Progress]]

## [[Tech-Glossary#Workstream|Workstreams]]

- [[workstreams/README]]
- [[workstreams/WS-01-Frontend]]
- [[workstreams/WS-02-Backend-and-Data]]
- [[workstreams/WS-03-Document-Processing-and-OCR]]
- [[workstreams/WS-04-Workflow-Orchestration]]
- [[workstreams/WS-05-Infrastructure-and-DevOps]]
- [[workstreams/WS-06-Quality-Testing-and-Documentation]]

## Product Requirements

- [[architecture/templates/PRD-Phase-0-Foundation]]
- [[architecture/templates/PRD-Phase-1-Document-Ingestion]]
- [[architecture/templates/PRD-Phase-2-OCR-Pipeline]]
- [[architecture/templates/PRD-Phase-3-AI-Extraction]]
- [[architecture/templates/PRD-Phase-4-Contract-Review-UI]]
- [[architecture/templates/PRD-Phase-5-Search-and-Knowledge-Base-RAG]]

## Architecture Decision Records

### Foundation

- [[architecture/templates/ADR-001-Monorepo]]
- [[architecture/templates/ADR-002-Docker-Compose]]
- [[architecture/templates/ADR-003-Repository-Structure]]
- [[architecture/templates/ADR-004-FastAPI-as-Backend-Framework]]
- [[architecture/templates/ADR-005-React-TypeScript-Vite]]
- [[architecture/templates/ADR-006-PostgreSQL-as-Primary-Database]]
- [[architecture/templates/ADR-007-Redis-as-Cache-and-Message-Broker]]
- [[architecture/templates/ADR-008-Celery-for-Background-Processing]]
- [[architecture/templates/ADR-009-n8n-for-Workflow-Orchestration]]

### [[Tech-Glossary#OCR|OCR]] & [[Tech-Glossary#AI|AI]]

- [[architecture/templates/ADR-010-OCR-Engine-Selection]]
- [[architecture/templates/ADR-011-OCR-Storage-Strategy]]
- [[architecture/templates/ADR-012-LLM-Provider-Selection]]
- [[architecture/templates/ADR-013-Prompt-Management-Strategy]]

### Review & [[Tech-Glossary#Audit Log|Audit]]

- [[architecture/templates/ADR-014-Review-State-Management]]
- [[architecture/templates/ADR-015-Audit-Logging-Strategy]]

### Search & [[Tech-Glossary#RAG|RAG]]

- [[architecture/templates/ADR-016-Vector-Database-Selection]]
- [[architecture/templates/ADR-017-Embedding-Model-Strategy]]
- [[architecture/templates/ADR-018-Document-Chunking-Strategy]]
- [[architecture/templates/ADR-019-Hybrid-Retrieval-Strategy]]
- [[architecture/templates/ADR-020-RAG-Orchestration]]

## Technical Areas

- [[frontend/README]]
- [[backend/README]]
- [[docker/README]]
- [[database/README]]
- [[security/README]]
- [[testing/Test-Strategy]]
- [[observability/README]]

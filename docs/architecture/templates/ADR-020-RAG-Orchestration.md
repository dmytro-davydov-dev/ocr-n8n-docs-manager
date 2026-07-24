# ADR-020 — RAG Orchestration

**Status:** Accepted
**Date:** 2026-07-24

## Context
Retrieval, prompt assembly and answer generation require a repeatable workflow.

## Decision
Use n8n to orchestrate the RAG pipeline while keeping retrieval and business logic in backend services. Pipeline: query → retrieval → reranking → prompt construction → LLM → citations → response.

## Rationale
- Clear orchestration
- Observable workflows
- Reusable components

## Alternatives
- Backend-only orchestration
- Agent framework

## Consequences
### Positive
- Easier monitoring
- Modular architecture

### Negative
- Additional orchestration layer

## Related Documents
- ADR-009-n8n
- PRD-Phase-5-Search-and-Knowledge-Base-RAG

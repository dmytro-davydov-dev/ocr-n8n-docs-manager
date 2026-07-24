# ADR-016 — Vector Database Selection

**Status:** Accepted
**Date:** 2026-07-24

## Context
The platform requires efficient semantic search, similarity search and RAG over contract documents.

## Decision
Use **pgvector** as the initial vector database by extending PostgreSQL.

## Rationale
- Single operational datastore
- Docker-friendly
- Excellent MVP fit
- Simple backup and migration
- Easy future migration to dedicated vector stores

## Alternatives Considered
- Qdrant
- Weaviate
- Milvus
- Pinecone

## Consequences
### Positive
- Lower operational complexity
- SQL + vector queries
- Tight integration with existing data

### Negative
- Less scalable than specialized engines

## Related Documents
- PRD-Phase-5-Search-and-Knowledge-Base-RAG
- ADR-006-PostgreSQL

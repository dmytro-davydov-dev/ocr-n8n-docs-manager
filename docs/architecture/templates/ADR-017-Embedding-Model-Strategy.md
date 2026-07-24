# ADR-017 — Embedding Model Strategy

**Status:** Accepted
**Date:** 2026-07-24

## Context
Semantic retrieval depends on high-quality embeddings while preserving provider flexibility.

## Decision
Introduce an embedding abstraction supporting OpenAI-compatible APIs and local embedding models. Persist embedding model name and version with every vector.

## Rationale
- Avoid vendor lock-in
- Support experimentation
- Enable re-indexing after model upgrades

## Alternatives
- Fixed embedding provider
- Database-generated embeddings

## Consequences
- Provider independence
- Requires embedding version management

## Related Documents
- ADR-012-LLM-Provider-Selection

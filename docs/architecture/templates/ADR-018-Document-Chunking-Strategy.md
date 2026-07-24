# ADR-018 — Document Chunking Strategy

**Status:** Accepted
**Date:** 2026-07-24

## Context
RAG quality depends heavily on how documents are divided before embedding.

## Decision
Chunk documents semantically using headings, clauses and paragraphs where possible, with configurable token limits and overlap. Store chunk metadata including page, section and offsets.

## Rationale
- Better retrieval accuracy
- Preserves context
- Supports precise citations

## Alternatives
- Fixed page chunks
- Fixed character windows

## Consequences
- Higher preprocessing complexity
- Better answer quality

## Related Documents
- PRD-Phase-5-Search-and-Knowledge-Base-RAG

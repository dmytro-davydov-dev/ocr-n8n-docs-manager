# ADR-019 — Hybrid Retrieval Strategy

**Status:** Accepted
**Date:** 2026-07-24

## Context
Pure vector search may miss exact legal terminology while keyword search misses semantic intent.

## Decision
Implement hybrid retrieval combining full-text search, metadata filters and vector similarity with configurable ranking.

## Rationale
- Higher recall
- Better precision
- Robust legal search

## Alternatives
- Vector-only
- Keyword-only

## Consequences
- Better retrieval quality
- More ranking logic

## Related Documents
- ADR-016-Vector-Database-Selection

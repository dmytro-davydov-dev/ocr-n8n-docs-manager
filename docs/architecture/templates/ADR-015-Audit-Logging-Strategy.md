# ADR-015 — Audit Logging Strategy

**Status:** Accepted
**Date:** 2026-07-24

# Context

Every modification to AI-generated data must be traceable for debugging, compliance, and future analytics.

# Decision

Maintain an immutable audit log separate from operational tables.

Each audit event records:

- document_id
- review_version
- user_id (or system actor)
- timestamp
- action
- field name
- previous value
- new value
- source (AI/User/System)

Audit records are append-only and never updated.

# Rationale

- Full traceability
- Easier debugging
- Compliance readiness
- Supports future event sourcing

# Alternatives Considered

- Store only latest values
- Database triggers only
- Application logs only

# Consequences

## Positive

- Complete history
- Easy rollback analysis
- Better observability

## Negative

- Increased storage
- Additional queries

## Risks

Large audit tables require indexing and archival policies.

# Related Documents

- PRD-Phase-4-Contract-Review-UI
- ADR-014-Review-State-Management

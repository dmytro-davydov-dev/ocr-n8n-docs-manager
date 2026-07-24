# ADR-014 — Review State Management

**Status:** Accepted
**Date:** 2026-07-24

# Context

Reviewed contracts transition through multiple lifecycle states while users may edit AI-generated data before approval. The application must preserve user changes, support future collaboration, and provide deterministic state transitions.

# Decision

Implement an explicit review state machine.

## States

- Uploaded
- OCR Completed
- AI Extracted
- Draft Review
- In Review
- Approved
- Rejected
- Archived

Only valid transitions are permitted. User edits create a new review version while preserving the original AI output.

# Rationale

- Predictable workflow
- Easier validation
- Future multi-user support
- Better auditability

# Alternatives Considered

- Boolean approved flag
- Free-form status values
- Workflow managed only in UI

# Consequences

## Positive

- Clear lifecycle
- Easier testing
- Extensible workflow

## Negative

- More backend logic
- State migration considerations

## Risks

Concurrent editing requires optimistic locking and version checks.

# Related Documents

- PRD-Phase-4-Contract-Review-UI
- ADR-013-Prompt-Management-Strategy

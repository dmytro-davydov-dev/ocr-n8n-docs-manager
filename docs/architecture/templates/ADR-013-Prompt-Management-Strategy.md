# ADR-013 — Prompt Management Strategy

**Status:** Accepted  
**Date:** 2026-07-24

# Context

Prompt engineering becomes a core part of the application. Prompt changes must be versioned, testable, auditable, and deployable independently of application code where practical.

# Decision

Store prompts as version-controlled Markdown or template files in the repository. Each extraction records:

- Prompt identifier
- Prompt version
- Model name
- Model version
- Execution timestamp

Production prompt changes require review and regression testing.

# Rationale

- Reproducible AI behavior
- Easier debugging
- Auditability
- Controlled evolution of prompts

# Alternatives Considered

- Inline prompts in source code
- Database-managed prompts only
- External prompt management service

# Consequences

## Positive

- Git history for prompt evolution
- Easy rollback
- Repeatable experiments

## Negative

- Additional maintenance
- Regression suite required

## Risks

- Prompt changes may unintentionally reduce extraction quality.

# Related Documents

- PRD-Phase-3-AI-Extraction
- ADR-012-LLM-Provider-Selection

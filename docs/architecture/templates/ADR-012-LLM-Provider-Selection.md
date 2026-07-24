# ADR-012 — LLM Provider Selection

**Status:** Accepted  
**Date:** 2026-07-24

# Context

The platform requires AI models to extract structured information from OCR text. The architecture must remain portable across cloud and self-hosted providers while supporting future experimentation and cost optimization.

# Decision

Adopt a provider-agnostic LLM abstraction layer. The initial implementation will target OpenAI-compatible APIs, while allowing additional providers (Anthropic, Google Gemini, Azure OpenAI, Ollama/vLLM, or other OpenAI-compatible endpoints) to be configured without changing business logic.

# Rationale

- Avoid vendor lock-in
- Enable A/B testing across providers
- Support local models for development or sensitive deployments
- Allow cost and latency optimization

# Alternatives Considered

- Hard-code a single provider
- Build separate integrations for each provider
- Use only local models

# Consequences

## Positive

- Flexible deployment
- Easier experimentation
- Future-proof architecture

## Negative

- Additional abstraction layer
- Slightly higher implementation complexity

## Risks

- Different models may produce different outputs, requiring regression tests.

# Related Documents

- PRD-Phase-3-AI-Extraction
- ADR-010-OCR-Engine-Selection

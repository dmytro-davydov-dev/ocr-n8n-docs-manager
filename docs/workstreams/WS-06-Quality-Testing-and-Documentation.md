# WS-06 — Quality, Testing, and Documentation

**Status:** Accepted
**Date:** 2026-07-24
**Owner:** Engineering (cross-cutting)

---

# Purpose

Own the cross-cutting practices that keep the other five workstreams honest and in sync: ADRs/PRDs, test strategy, CI verification, and the Obsidian knowledge base. This workstream doesn't block feature work — it gates merges and keeps the project's documented architecture true to what's actually running.

---

# Scope

- ADR and PRD authoring/maintenance (`docs/architecture/templates/`).
- `docs/MOC.md` and `docs/Progress.md` upkeep.
- Test strategy across unit, integration, and regression tests for every workstream.
- CI configuration: contract-drift checks (OpenAPI/client), migration checks, formatting/linting.
- Phase acceptance verification (`make verify-phase0` and successors).
- Fixtures under `fixtures/` (synthetic/legally distributable documents and expected results).

---

# Responsibilities

- Keep every ADR/PRD's `Related Documents` links and status current as decisions are superseded.
- Define and maintain the integration-test suite that exercises the WS-01→WS-02→WS-03→WS-04 seams end to end.
- Own regression fixtures for OCR and AI extraction so provider/model/prompt changes are caught (ADR-010, ADR-012, ADR-013).
- Verify each phase's acceptance criteria before it's marked complete in `Progress.md`.
- Flag documentation drift (a workstream doc whose `Consumes`/`Produces` no longer match reality) as a review blocker, same as a failing test.

---

# Out of Scope

- Implementing the feature code being tested (owned by the respective workstream).
- Making architectural decisions unilaterally — WS-06 facilitates and records ADRs, it doesn't override the owning workstream's technical call.

---

# Deliverables

- ADR-001 through ADR-020 and PRD-Phase-0 through PRD-Phase-5 (ongoing, living documents).
- `make verify-phase0` and phase-specific verification targets.
- Backend auth regression test (`test_internal_api_auth.py`) and equivalents per phase.
- OCR/extraction regression fixture sets (Phase 2–3).
- Retrieval evaluation harness for hybrid search/RAG (Phase 5).

---

# Dependencies

- **Depends on all workstreams** having something to test/document — it consumes their contracts and outputs but does not block their initial implementation.
- **Gates all workstreams' merges** via CI: this is the one place where "cross-cutting" means "authoritative on quality bar," even though it owns no product surface.

---

# Consumes

- OpenAPI spec (WS-02), workflow exports (WS-04), Compose health checks (WS-05), task contracts (WS-03), and UI build output (WS-01) — as inputs to tests and documentation, not as implementation dependencies.

# Produces

- CI gates (contract drift, migrations, lint/format, test suites) that every workstream's PRs must pass.
- Up-to-date ADRs/PRDs/MOC that other workstreams rely on as the source of truth for "why" and "what's next."
- Regression fixtures that WS-03 uses to detect quality regressions from provider/prompt changes.

---

# Milestones by Phase

| Phase | Milestone |
|---|---|
| 0 | ADR-001–009, PRD-0 complete; `make verify-phase0` passes; auth regression test in place. |
| 1 | Ingestion integration tests (upload → metadata → workflow trigger). |
| 2 | OCR regression fixtures; multi-page processing test coverage. |
| 3 | Extraction schema validation tests; prompt regression suite. |
| 4 | Review/audit integration tests (edit → save → approve → audit trail). |
| 5 | Retrieval evaluation harness; citation-accuracy checks. |

---

# Done Criteria

- Every ADR has Status/Date/Related Documents current.
- `docs/MOC.md` links to every ADR/PRD/workstream doc.
- CI blocks merges on contract drift, failing tests, and migration errors.
- Each phase's `Progress.md` entry reflects verified (not assumed) completion.

---

# Risks

| Risk | Mitigation |
|---|---|
| Docs drift from actual implementation | Treat stale `Consumes`/`Produces` sections as a review blocker. |
| Test suite lags feature delivery | Require test/doc updates in the same PR as the feature. |
| Regression fixtures become stale | Refresh fixtures when OCR/LLM providers or prompts change. |

---

# Future Evolution

- Add contract testing (e.g., schema-based consumer/provider tests) between WS-01 and WS-02 as the API surface grows.
- Expand retrieval evaluation with labeled query sets once Phase 5 ships.

---

# Related Documents

- [[README]]
- [[../MOC]]
- [[../Progress]]
- All ADRs and PRDs under `docs/architecture/templates/`

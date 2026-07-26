# Test Strategy

## Current state

Automated coverage is backend-only: a Python `unittest` suite (`apps/backend/tests/`), 57 tests as of the last recorded run ([[architecture/Progress.md]]). There is no automated frontend test suite yet (verification there has been `tsc -b` / `vite build` plus manual/mock-driven checks — see [[../frontend/README|Frontend]] Known Gaps).

## Backend suite

Location: `apps/backend/tests/`. Runs against an in-memory SQLite database (`create_engine("sqlite:///:memory:", ...)`, `StaticPool`) with `Base.metadata.create_all()` — not the real Postgres — so tests are fast and hermetic. External providers (OCR engine, LLM, embeddings) are always faked/mocked; none of the following have ever been run against a real paddleocr/LLM/embedding backend inside the test suite itself (real-provider runs have been done manually against the live stack, see [[architecture/Progress.md]] Technical Debt).

| File | Covers |
| --- | --- |
| `test_internal_api_auth.py` | `X-Internal-Api-Key` enforcement on `/api/internal/*` |
| `test_documents_api.py` | Upload/list/get/file endpoints, status transitions |
| `test_reviews_api.py` | Full review lifecycle: create → draft edits → submit → approve/reject/revise/archive, optimistic-lock (412) and validation (422) errors |
| `test_ocr_pipeline.py` | `validate_file`/`run_ocr` idempotency, retry-vs-terminal failure classification, `/ocr` response contract, using a fake `OcrEngine` |
| `test_ai_pipeline.py` | `extract_fields`/`generate_embeddings`: idempotency, retry-vs-terminal classification (including schema-validation failures), stale-chunk cleanup, using fake LLM/embedding providers |
| `test_internal_processing.py` | `/process`/`/reprocess` dispatch, auth, 404s, the 409 "already in flight" guard |
| `test_search_and_chat.py` | Hybrid search ranking, the FR-501 approved-only filter, `/search` and `/chat` end-to-end with fake providers, 503s when a provider is unavailable |
| `test_ingestion_integration.py` | End-to-end seam: real upload → webhook trigger → `/process` → the real task chain (only OCR/LLM/embedding providers faked) → document reaches `complete` with OCR/extraction/chunks populated |
| `test_regression_fixtures.py` | Replays the checked-in `fixtures/ocr_extraction/` golden files through the real pipeline plumbing and asserts persisted output matches exactly (prompt/schema regression baseline) |

## Running tests

```bash
make test-backend          # full suite
make test-backend-auth      # auth test only
```

Both targets run against a local Python venv if `fastapi` is importable there, otherwise fall back to `docker compose run --rm backend python -m unittest ...`. Keep the backend image rebuilt (`docker compose build backend celery-worker`) when relying on the Docker fallback — a stale image has previously run a smaller/older test count than the local venv, silently masking newly added tests (see [[architecture/Progress.md]]).

Or directly:

```bash
cd apps/backend
python -m unittest discover -v -s tests
```

## Fixtures

`fixtures/ocr_extraction/` holds a synthetic 2-page contract PDF plus golden `*.ocr.json`/`*.extraction.json` files that `test_regression_fixtures.py` asserts the pipeline reproduces exactly — a prompt/schema-regression baseline per [[../architecture/templates/ADR-013-Prompt-Management-Strategy|ADR-013]], meant to be refreshed in the same PR as any OCR engine, LLM, or prompt change. Note: real paddleocr output does not match this golden file byte-for-byte (a known digit/letter OCR artifact) — the fixture is a regression baseline against the fake engine used in tests, not a claim about real OCR accuracy.

## CI

`.github/workflows/backend.yml` runs on a `pgvector/pgvector:pg16` service container:

1. Run the `unittest` suite.
2. `alembic upgrade head` against the real Postgres service (catches migrations that don't apply cleanly).
3. `alembic check` (catches model/migration drift — has caught real bugs, e.g. indexes declared in a migration but not on the corresponding model).
4. `make verify-openapi` (fails the build if `packages/api-client/openapi.json` is out of date with the actual routes/schemas — regenerate with `make export-openapi`).

## Manual/live-stack verification

Several behaviors are only verified by driving the real Docker Compose stack by hand, not by the automated suite — notably real paddleocr OCR output, and real OpenAI-compatible LLM/embedding HTTP calls against a throwaway stub server. These sessions are logged in detail in [[architecture/Progress.md]] (Completed / Technical Debt sections) rather than captured as repeatable automated tests. `make verify-phase0` and `make verify-infra` are the closest thing to automated live-stack checks — they assert service reachability and infra invariants (pgvector enabled, n8n's Postgres role is isolated) against a running stack, not application behavior.

## Known gaps

- No frontend automated tests (unit, component, or e2e) — see [[../frontend/README|Frontend]].
- No test has exercised OCR/LLM/embeddings against a real, non-fake provider from within the test suite itself.
- The review workspace UI has never been verified via an actual browser click-through in this environment (Chrome automation was unavailable in every session that touched it).
- No load/performance testing.

## Related

- [[../backend/README]]
- [[../architecture/Progress.md]]
- [[../architecture/templates/ADR-013-Prompt-Management-Strategy]]
- [[../workstreams/WS-06-Quality-Testing-and-Documentation]]

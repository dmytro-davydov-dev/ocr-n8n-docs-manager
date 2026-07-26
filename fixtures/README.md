# Fixtures

Synthetic, legally distributable documents (and their expected pipeline
output) used by WS-06's regression tests. Nothing here is a real contract —
every document is authored for testing.

## `ocr_extraction/`

Regression fixture set for WS-03's OCR and extraction pipeline (ADR-010,
ADR-012, ADR-013), consumed by
`apps/backend/tests/test_regression_fixtures.py`:

- `sample_contract.pdf` — synthetic 2-page PDF (generated with PyMuPDF)
  containing fabricated contract boilerplate: two parties, an effective
  date, a termination date, a monthly fee, and confidentiality/governing-law
  clauses.
- `sample_contract.ocr.json` — the expected per-page OCR output
  (`extracted_text`/`confidence_score`) for that PDF. Pins the exact text
  the pipeline should persist so a change to page rasterization, upsert
  logic, or response shape shows up as a diff instead of a silent drift.
- `sample_contract.extraction.json` — the expected `ExtractedContractFields`
  the LLM extraction step should produce from that OCR text. Acts as the
  prompt-regression baseline for `contract_extraction_v1.md`
  (ADR-013): if a prompt or schema change shifts what a real LLM would
  return, update this file deliberately in the same PR, not as a side
  effect.

## Refreshing fixtures

Per the WS-06 Risks table ("Regression fixtures become stale"): update
`*.ocr.json`/`*.extraction.json` in the same PR that changes the OCR engine,
LLM provider, prompt version, or the pipeline's persisted schema — never
let the checked-in expectation silently diverge from what the pipeline
actually does today.

`sample_contract.ocr.json` was captured from the fake engine
`test_regression_fixtures.py` uses, not real `paddleocr` — its text doesn't
byte-for-byte match what real paddleocr produces (Progress.md Blockers #5,
e.g. a digit/letter artifact like `$5,ooo.00`). Regenerate it from a real
paddleocr run with:

```bash
make refresh-ocr-fixture
```

(`apps/backend/scripts/refresh_ocr_fixture.py`, run inside the
`celery-worker` container since that's the image with the real
paddleocr/paddlepaddle native dependencies proven to work.) Review the diff
before committing — this is a deliberate, reviewed update, same as any other
fixture refresh, not a rubber-stamped overwrite.

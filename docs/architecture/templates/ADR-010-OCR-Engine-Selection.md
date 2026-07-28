# ADR-010 — OCR Engine Selection

**Status:** Accepted  
**Date:** 2026-07-24

# Context

The platform requires a self-hosted OCR engine that integrates with Docker, Celery, and n8n while supporting scanned PDFs and images.

# Decision

Use **PaddleOCR** as the primary OCR engine behind an internal OCR service.

# Rationale

- High OCR accuracy
- Good support for multi-language documents
- Container-friendly
- Active open-source community
- Suitable for future layout-aware extraction

# Alternatives Considered

- Tesseract
- OCRmyPDF
- Cloud OCR APIs

# Consequences

## Positive

- Fully self-hosted
- No vendor lock-in
- Easy Docker deployment
- Works offline

## Negative

- Higher CPU usage than Tesseract
- Additional model management

## Risks

- Future model upgrades may require regression testing.

# Addendum (2026-07-28): PaddleOCR CPU Memory Leak — Tesseract Added

## Context

A real uploaded document ("CONTRATO DE TRABALHO ... signed1.pdf", 6 pages,
300.5KB, standard A4 pages) got permanently stuck in `processing`, never
reaching `complete` or `failed`. Investigating this surfaced three distinct,
stacked problems in the processing pipeline before reaching the actual OCR
engine issue this addendum is about — see `docs/architecture/Progress.md`
for the full write-up of each:

1. Celery tasks never handled `MaxRetriesExceededError` (retries exhausted)
   or configured any `time_limit`, so a task could die or hang without ever
   persisting a terminal `failed` status.
2. `celery_app.py` never set `task_acks_late`, so a worker killed mid-task
   lost its message entirely rather than having it redelivered.
3. PaddlePaddle JIT-compiles a native C++ extension on first use, specific
   to the container's CPU/arch; this compile alone spiked RSS to several GB
   and got OOM-killed, and because a fresh Celery pool worker never inherits
   a sibling's completed compile, this became an unrecoverable
   compile → OOM → new worker → compile → OOM loop.

Fixing all three did **not** fix the stuck document. The real cause was
found by direct measurement, live, with the user watching `docker stats`
during a reprocess attempt:

## Root Cause

**PaddleOCR/PaddlePaddle has a confirmed, upstream, unfixed native (C++)
memory leak on CPU inference across sequential calls within one process.**
This is documented in multiple open PaddlePaddle/PaddleOCR GitHub issues
(e.g. [#15631](https://github.com/PaddlePaddle/PaddleOCR/issues/15631),
[#17955](https://github.com/PaddlePaddle/PaddleOCR/issues/17955),
[#16173](https://github.com/PaddlePaddle/PaddleOCR/issues/16173)),
independent of this project's specific version pins or Docker setup.

Evidence gathered before concluding this:

- Moving the JIT compile to Docker build time (a separate, real fix, kept)
  eliminated the "No ccache found" warning at runtime but did **not** stop
  the OOM — ruling out the compile as the (sole) cause.
- Reprocessing `fixtures/ocr_extraction/sample_contract.pdf` (2 pages)
  completed successfully under the exact same image; the real 6-page
  document still got OOM-killed every time. Page dimensions were confirmed
  normal (595×842pt, standard A4, ~11.6MB raw RGB per rendered page at 200
  DPI) via a `fitz`-based inspection inside the container — ruling out a
  malformed/oversized page.
- `git diff` against commit `9384742` ("verify real OCR works") showed
  `requirements.txt` and `app/services/ocr_engine.py` byte-for-byte
  unchanged — ruling out a regression in this project's own code or
  dependency versions. The only variable was page *count* processed
  sequentially by one long-lived `PaddleOCR` instance within a single
  `run_ocr` call.
- Adding an explicit `del` + `gc.collect()` after each page in `run_ocr`'s
  loop (targeting "the leak is in Python-reachable objects") did **not**
  stop the growth — confirming the leak lives inside PaddlePaddle's own
  native runtime/allocator, below what Python-level garbage collection can
  reach.

## Decision

Add **Tesseract** (`pytesseract` + the `tesseract-ocr` system binary) as a
second, fully-supported `OcrEngine` implementation
(`app/services/ocr_engine.py:TesseractOcrEngine`), selectable via the
existing `OCR_ENGINE` config (ADR-010's original "swappable via
configuration, not code changes" requirement). `OCR_ENGINE=tesseract` is
the practical recommendation for CPU-only deployments until/unless the
upstream PaddlePaddle leak is fixed; `paddleocr` remains a valid
configuration (dependencies kept installed) for anyone who wants PaddleOCR's
higher accuracy on GPU or has verified their deployment doesn't hit this
leak, but it should be treated as fragile on CPU-only hosts.

Rejected: subprocess-isolating each page's PaddleOCR call (would force the
OS to reclaim the leaked native memory when the subprocess exits, likely
actually fixing it) — real engineering effort with real per-page latency
cost, for a dependency that has now cost this project three separate
platform-specific failures (an ARM64 segfault, a missing-`setuptools`
import failure, and this leak). Tesseract sidesteps the whole class of
problem (no ML-framework native memory-pool/runtime-cache layer to leak)
rather than working around it.

Verified live (not just reasoned about): `TesseractOcrEngine.recognize_page`
correctly recognizes real rendered text and reports a real engine version
against the actual `tesseract` binary; 30 repeated calls against the same
image showed **zero** RSS growth (flat at ~87MB), unlike PaddleOCR's
multi-GB climb on a 6-page document. See
`apps/backend/tests/test_ocr_engine.py`.

## Consequences

### Positive

- CPU-only deployments have a real, working, memory-stable OCR path.
- No PaddleOCR/PaddlePaddle code removed — `OCR_ENGINE=paddleocr` still
  works for anyone who wants it and doesn't hit the leak (e.g. small
  single-page documents, or a GPU deployment).
- `run_ocr`'s time-limit/retry-exhaustion handling (fixed in the same
  investigation) means that even if a leak-prone engine does OOM a worker
  in the future, the document now reaches a visible `failed` state instead
  of hanging forever, and the `/reprocess` staleness-gated override exists
  to recover it.

### Negative

- Tesseract's accuracy is generally lower than PaddleOCR's PP-OCRv4 models
  for complex, rotated, or dense multilingual layouts.
- Language is not currently tied to actual document-language detection for
  either engine (`OCR_TESSERACT_LANG`, default `eng`, is a static config
  value, not per-document) — a known gap, not new to this addendum.
- Two OCR engines to maintain/document instead of one.

## Related Documents

- PRD-Phase-2-OCR-Pipeline
- ADR-009-n8n
- `docs/architecture/Progress.md` (full investigation timeline)

"""Regenerate fixtures/ocr_extraction/sample_contract.ocr.json from a real
paddleocr run, instead of the fake engine test_regression_fixtures.py uses.

Progress.md Blockers #5: the checked-in golden file was captured from a
different (fake/fixture) OCR path and doesn't byte-for-byte match real
paddleocr's output (e.g. a digit/letter artifact like "$5,ooo.00"). Refresh it
here so it becomes a real accuracy baseline instead of a fixture-vs-fixture
tautology. Rerun (and commit the diff deliberately) any time the OCR engine,
its version, or the rasterization DPI changes -- see fixtures/README.md.

This needs the real paddleocr/paddlepaddle native dependencies (heavy, and
not always installable on every dev machine/architecture -- see the backend
Dockerfile and requirements.txt comments on the aarch64 segfault this project
already hit once). Run it inside the celery-worker container, where those
dependencies are already proven to work:

    docker compose run --rm celery-worker python scripts/refresh_ocr_fixture.py

or via `make refresh-ocr-fixture`, which does the same thing.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import fitz  # PyMuPDF

from app.core.config import settings
from app.services.ocr_engine import PaddleOcrEngine

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_PDF = REPO_ROOT / "fixtures" / "ocr_extraction" / "sample_contract.pdf"
FIXTURE_OCR_JSON = REPO_ROOT / "fixtures" / "ocr_extraction" / "sample_contract.ocr.json"


def main() -> None:
    if not FIXTURE_PDF.exists():
        print(f"{FIXTURE_PDF} does not exist.", file=sys.stderr)
        raise SystemExit(1)

    print(f"Loading real PaddleOcrEngine (OCR_ENGINE={settings.ocr_engine!r} is not consulted; "
          f"this script always instantiates PaddleOcrEngine directly)...")
    engine = PaddleOcrEngine()
    print(f"Engine ready: paddleocr:{engine.engine_version}")

    content = FIXTURE_PDF.read_bytes()
    pdf = fitz.open(stream=content, filetype="pdf")

    pages = []
    try:
        zoom = settings.ocr_rasterize_dpi / 72
        matrix = fitz.Matrix(zoom, zoom)
        for page_index in range(pdf.page_count):
            page = pdf.load_page(page_index)
            pixmap = page.get_pixmap(matrix=matrix)
            image_bytes = pixmap.tobytes("png")

            result = engine.recognize_page(image_bytes)
            print(f"Page {page_index + 1}: confidence={result.confidence:.4f}")
            pages.append(
                {
                    "page_number": page_index + 1,
                    "extracted_text": result.text,
                    "confidence_score": round(result.confidence, 4),
                }
            )
    finally:
        pdf.close()

    FIXTURE_OCR_JSON.write_text(json.dumps({"pages": pages}, indent=2) + "\n")
    print(f"Wrote real paddleocr:{engine.engine_version} output to {FIXTURE_OCR_JSON}")
    print(
        "Review the diff before committing -- this is meant to be a deliberate, "
        "reviewed update (fixtures/README.md), not a silent overwrite."
    )


if __name__ == "__main__":
    main()

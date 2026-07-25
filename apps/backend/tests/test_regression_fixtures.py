"""WS-06: OCR/extraction regression fixtures (Phase 2/3 milestones).

Runs the real pipeline plumbing (validate_file -> run_ocr -> extract_fields)
against the checked-in synthetic contract under
`fixtures/ocr_extraction/` and asserts the persisted output matches the
golden `*.ocr.json`/`*.extraction.json` fixtures exactly. A real OCR engine
(paddleocr) and LLM can't run in this dev shell (see Progress.md Technical
Debt), so the OCR/LLM steps are driven by fixture-backed fakes that replay
the checked-in golden text/JSON -- this test's job is to catch drift in the
pipeline's own handling of that data (page ordering, persisted schema,
prompt/model bookkeeping), not OCR/LLM accuracy itself. Refresh the fixture
files in the same PR as any OCR engine/LLM/prompt change, per the WS-06
Risks table.
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.storage import LocalDocumentStorage
from app.main import app
from app.models import Base
from app.repositories import document_repository
from app.services.llm_provider import LlmCompletionResult
from app.services.ocr_engine import PageOcrResult
import app.tasks.extraction as extraction_module
import app.tasks.file_validation as file_validation_module
import app.tasks.ocr as ocr_module
from app.tasks.extraction import extract_fields
from app.tasks.file_validation import validate_file
from app.tasks.ocr import run_ocr

def _fixtures_dir() -> Path:
    """Locate `fixtures/ocr_extraction` in both layouts this suite runs in:
    local dev (apps/backend/tests/<file> -> repo root is 3 parents up) and
    the backend container (build context is apps/backend, so the repo-root
    `fixtures/` is bind-mounted at `/app/fixtures` instead -- see
    docker-compose.yml's `backend` service volumes)."""
    here = Path(__file__).resolve()
    candidates = [here.parent.parent / "fixtures" / "ocr_extraction"]
    if len(here.parents) > 3:
        candidates.append(here.parents[3] / "fixtures" / "ocr_extraction")
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"Could not locate fixtures/ocr_extraction; checked {candidates}")


FIXTURES_DIR = _fixtures_dir()


class FixtureOcrEngine:
    """Replays the golden `sample_contract.ocr.json` pages in order,
    regardless of the rasterized image bytes it's called with -- a stand-in
    for a real OCR engine, not a model of one."""

    engine_name = "fixture"
    engine_version = "1"

    def __init__(self, pages: list[dict]) -> None:
        self._pages = pages
        self.calls = 0

    def recognize_page(self, image_bytes: bytes) -> PageOcrResult:
        result = self._pages[self.calls]
        self.calls += 1
        return PageOcrResult(text=result["extracted_text"], confidence=result["confidence_score"])


class FixtureLlmProvider:
    """Replays the golden `sample_contract.extraction.json` content -- a
    stand-in for a real LLM call, not a model of one."""

    provider_name = "fixture-llm"
    model_name = "fixture-model"

    def __init__(self, content: dict) -> None:
        self._content = content
        self.calls = 0

    def complete_json(self, *, system_prompt: str, user_content: str) -> LlmCompletionResult:
        self.calls += 1
        return LlmCompletionResult(raw_content=json.dumps(self._content), model_name=self.model_name)


class OcrExtractionFixtureRegressionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

        self.tmpdir = tempfile.TemporaryDirectory()
        self.storage = LocalDocumentStorage(self.tmpdir.name)

        self.patches = [
            patch.object(file_validation_module, "SessionLocal", self.SessionLocal),
            patch.object(ocr_module, "SessionLocal", self.SessionLocal),
            patch.object(extraction_module, "SessionLocal", self.SessionLocal),
            patch.object(file_validation_module, "storage", self.storage),
            patch.object(ocr_module, "storage", self.storage),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self) -> None:
        for p in self.patches:
            p.stop()
        app.dependency_overrides.clear()
        self.tmpdir.cleanup()
        Base.metadata.drop_all(self.engine)

    def test_pipeline_output_matches_golden_fixture(self) -> None:
        pdf_bytes = (FIXTURES_DIR / "sample_contract.pdf").read_bytes()
        expected_ocr = json.loads((FIXTURES_DIR / "sample_contract.ocr.json").read_text())["pages"]
        expected_extraction = json.loads((FIXTURES_DIR / "sample_contract.extraction.json").read_text())

        db = self.SessionLocal()
        try:
            stored = self.storage.save("fixture-doc", "sample_contract.pdf", pdf_bytes)
            document = document_repository.create(
                db,
                document_id="fixture-doc",
                filename="sample_contract.pdf",
                content_type="application/pdf",
                size_bytes=stored.size_bytes,
                content_hash=stored.content_hash,
                storage_path=stored.storage_path,
                actor="test",
            )
            document_repository.update_status(db, document, new_status="queued", actor="test")
        finally:
            db.close()

        self.assertEqual(validate_file("fixture-doc"), "processing")

        fixture_engine = FixtureOcrEngine(expected_ocr)
        self.assertEqual(run_ocr("fixture-doc", engine=fixture_engine), "complete")
        self.assertEqual(fixture_engine.calls, len(expected_ocr))

        ocr_response = self.client.get("/api/documents/fixture-doc/ocr")
        self.assertEqual(ocr_response.status_code, 200)
        actual_pages = ocr_response.json()
        self.assertEqual(len(actual_pages), len(expected_ocr))
        for actual, expected in zip(actual_pages, expected_ocr):
            self.assertEqual(actual["pageNumber"], expected["page_number"])
            self.assertEqual(actual["extractedText"], expected["extracted_text"])
            self.assertAlmostEqual(actual["confidenceScore"], expected["confidence_score"])

        fixture_provider = FixtureLlmProvider(expected_extraction)
        self.assertEqual(extract_fields("fixture-doc", provider=fixture_provider), "extracted")

        extraction_response = self.client.get("/api/documents/fixture-doc/extraction")
        self.assertEqual(extraction_response.status_code, 200)
        self.assertEqual(extraction_response.json()["content"], expected_extraction)


if __name__ == "__main__":
    unittest.main()

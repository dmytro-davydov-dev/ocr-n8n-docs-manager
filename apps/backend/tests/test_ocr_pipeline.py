import tempfile
import unittest
from unittest.mock import patch

import fitz
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.storage import LocalDocumentStorage
from app.main import app
from app.models import Base
from app.repositories import document_repository
from app.services.ocr_engine import PageOcrResult
import app.tasks.file_validation as file_validation_module
import app.tasks.ocr as ocr_module
from app.tasks.file_validation import validate_file
from app.tasks.ocr import run_ocr


def _sample_pdf(page_count: int = 2) -> bytes:
    pdf = fitz.open()
    for i in range(page_count):
        page = pdf.new_page()
        page.insert_text((72, 72), f"Hello page {i + 1}")
    content = pdf.tobytes()
    pdf.close()
    return content


class FakeOcrEngine:
    engine_name = "fake"
    engine_version = "1"

    def __init__(
        self,
        text: str = "recognized text",
        confidence: float = 0.95,
        error: Exception | None = None,
        fail_after: int | None = None,
    ):
        self._text = text
        self._confidence = confidence
        self._error = error
        self._fail_after = fail_after
        self.calls = 0

    def recognize_page(self, image_bytes: bytes) -> PageOcrResult:
        self.calls += 1
        if self._error is not None and (self._fail_after is None or self.calls > self._fail_after):
            raise self._error
        return PageOcrResult(text=self._text, confidence=self._confidence)


class OcrPipelineTest(unittest.TestCase):
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

        self.session_local_patches = [
            patch.object(file_validation_module, "SessionLocal", self.SessionLocal),
            patch.object(ocr_module, "SessionLocal", self.SessionLocal),
        ]
        self.storage_patches = [
            patch.object(file_validation_module, "storage", self.storage),
            patch.object(ocr_module, "storage", self.storage),
        ]
        for p in self.session_local_patches + self.storage_patches:
            p.start()

    def tearDown(self) -> None:
        for p in self.session_local_patches + self.storage_patches:
            p.stop()
        app.dependency_overrides.clear()
        self.tmpdir.cleanup()
        Base.metadata.drop_all(self.engine)

    _STATUS_PATH = {
        "uploaded": [],
        "queued": ["queued"],
        "processing": ["queued", "processing"],
        "complete": ["queued", "processing", "complete"],
        "failed": ["queued", "failed"],
    }

    def _make_document(self, status: str, content: bytes | None = None, content_type: str = "application/pdf"):
        content = content if content is not None else _sample_pdf()
        db = self.SessionLocal()
        try:
            stored = self.storage.save("doc-1", "contract.pdf", content)
            document = document_repository.create(
                db,
                document_id="doc-1",
                filename="contract.pdf",
                content_type=content_type,
                size_bytes=stored.size_bytes,
                content_hash=stored.content_hash,
                storage_path=stored.storage_path,
                actor="test",
            )
            for target in self._STATUS_PATH[status]:
                document = document_repository.update_status(db, document, new_status=target, actor="test")
            return document.id
        finally:
            db.close()

    # -- validate_file --------------------------------------------------

    def test_validate_file_advances_queued_valid_pdf_to_processing(self) -> None:
        document_id = self._make_document("queued")

        result = validate_file(document_id)

        self.assertEqual(result, "processing")
        db = self.SessionLocal()
        self.assertEqual(document_repository.get(db, document_id).status, "processing")
        db.close()

    def test_validate_file_marks_non_pdf_as_failed(self) -> None:
        document_id = self._make_document("queued", content=b"not a pdf at all")

        result = validate_file(document_id)

        self.assertEqual(result, "failed")
        db = self.SessionLocal()
        document = document_repository.get(db, document_id)
        self.assertEqual(document.status, "failed")
        self.assertIn("PDF", document.error_message)
        db.close()

    def test_validate_file_is_idempotent_on_duplicate_delivery(self) -> None:
        document_id = self._make_document("queued")

        first = validate_file(document_id)
        second = validate_file(document_id)

        self.assertEqual(first, "processing")
        self.assertEqual(second, "processing")  # no-op: already advanced past 'queued'

    # -- run_ocr ----------------------------------------------------------

    def test_run_ocr_persists_pages_and_completes_document(self) -> None:
        document_id = self._make_document("processing")
        fake_engine = FakeOcrEngine(text="extracted", confidence=0.88)

        result = run_ocr(document_id, engine=fake_engine)

        self.assertEqual(result, "complete")
        self.assertEqual(fake_engine.calls, 2)

        db = self.SessionLocal()
        self.assertEqual(document_repository.get(db, document_id).status, "complete")
        db.close()

        response = self.client.get(f"/api/documents/{document_id}/ocr")
        self.assertEqual(response.status_code, 200)
        pages = response.json()
        self.assertEqual(len(pages), 2)
        self.assertEqual(pages[0]["pageNumber"], 1)
        self.assertEqual(pages[0]["extractedText"], "extracted")
        self.assertAlmostEqual(pages[0]["confidenceScore"], 0.88)
        self.assertEqual(pages[0]["ocrEngineVersion"], "fake:1")
        self.assertIn("processingTimestamp", pages[0])
        self.assertEqual(pages[0]["documentId"], document_id)

    def test_run_ocr_upsert_avoids_duplicates_on_retried_delivery(self) -> None:
        """A run that fails partway through (page 1 persisted, page 2
        transiently fails) leaves the document 'processing'. Celery's
        at-least-once delivery means the task runs again from page 1 —
        that must overwrite, not duplicate, the already-persisted page."""
        document_id = self._make_document("processing")
        flaky_engine = FakeOcrEngine(text="first pass", error=TimeoutError("boom"), fail_after=1)

        # Calling the task function directly (not via apply_async) means
        # Celery's self.retry() has no real request to reschedule, so it
        # re-raises the original exception instead of `Retry` -- this still
        # exercises the retry code path and lets us assert the document is
        # left in a retry-safe state rather than marked 'failed'.
        with self.assertRaises(TimeoutError):
            run_ocr(document_id, engine=flaky_engine)

        db = self.SessionLocal()
        self.assertEqual(document_repository.get(db, document_id).status, "processing")
        db.close()

        result = run_ocr(document_id, engine=FakeOcrEngine(text="second pass"))
        self.assertEqual(result, "complete")

        response = self.client.get(f"/api/documents/{document_id}/ocr")
        pages = response.json()
        self.assertEqual(len(pages), 2)
        self.assertTrue(all(p["extractedText"] == "second pass" for p in pages))

    def test_run_ocr_completed_document_is_a_noop(self) -> None:
        document_id = self._make_document("processing")
        run_ocr(document_id, engine=FakeOcrEngine())

        second_engine = FakeOcrEngine()
        result = run_ocr(document_id, engine=second_engine)

        self.assertEqual(result, "complete")
        self.assertEqual(second_engine.calls, 0)

    def test_run_ocr_retries_on_transient_engine_failure_without_failing_document(self) -> None:
        document_id = self._make_document("processing")
        flaky_engine = FakeOcrEngine(error=TimeoutError("provider timeout"))

        # Calling the task function directly (not via apply_async) means
        # Celery's self.retry() has no real request to reschedule, so it
        # re-raises the original exception instead of `Retry` -- this still
        # exercises the retry code path and lets us assert the document is
        # left in a retry-safe state rather than marked 'failed'.
        with self.assertRaises(TimeoutError):
            run_ocr(document_id, engine=flaky_engine)

        db = self.SessionLocal()
        document = document_repository.get(db, document_id)
        db.close()
        # Still 'processing', not 'failed' -- transient failures stay retryable.
        self.assertEqual(document.status, "processing")

    def test_run_ocr_skips_document_not_in_processing(self) -> None:
        document_id = self._make_document("queued")

        result = run_ocr(document_id, engine=FakeOcrEngine())

        self.assertEqual(result, "queued")


if __name__ == "__main__":
    unittest.main()

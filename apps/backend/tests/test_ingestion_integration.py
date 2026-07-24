"""WS-06 Phase 1 milestone: ingestion integration tests (upload -> metadata
-> workflow trigger), extended through the full processing chain.

Unlike the per-task unit tests in test_documents_api.py/test_ocr_pipeline.py/
test_ai_pipeline.py/test_internal_processing.py (which each exercise one
workstream's slice in isolation, or dispatch the chain with `chain` mocked
away entirely), this test drives the actual cross-workstream seam end to
end in one run: WS-01's upload contract -> WS-02's document API -> the
outbound n8n workflow-trigger webhook (WS-04) -> the internal `/process`
endpoint n8n calls back into (ADR-009) -> the real validate_file/run_ocr/
extract_fields/generate_embeddings task chain (WS-03), with only the
external OCR/LLM/embedding providers faked (they aren't runnable in this
dev shell -- see Progress.md Technical Debt). Everything else -- status
transitions, audit logging, persistence, response shapes -- is the real
implementation.
"""

import json
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import fitz
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import get_db
from app.core.storage import LocalDocumentStorage
from app.main import app
from app.models import Base
import app.services.document_service as document_service_module
import app.tasks.embeddings as embeddings_module
import app.tasks.extraction as extraction_module
import app.tasks.file_validation as file_validation_module
import app.tasks.ocr as ocr_module
from app.services.embedding_provider import EmbeddingResult
from app.services.llm_provider import LlmCompletionResult
from app.services.ocr_engine import PageOcrResult
from app.tasks.embeddings import generate_embeddings
from app.tasks.extraction import extract_fields
from app.tasks.file_validation import validate_file
from app.tasks.ocr import run_ocr


def _sample_pdf() -> bytes:
    pdf = fitz.open()
    page = pdf.new_page()
    page.insert_text((72, 72), "Integration test contract body.")
    content = pdf.tobytes()
    pdf.close()
    return content


class FakeOcrEngine:
    engine_name = "fake"
    engine_version = "1"

    def recognize_page(self, image_bytes: bytes) -> PageOcrResult:
        return PageOcrResult(text="Integration test contract body.", confidence=0.93)


class FakeLlmProvider:
    provider_name = "fake-llm"
    model_name = "fake-model"

    def complete_json(self, *, system_prompt: str, user_content: str) -> LlmCompletionResult:
        content = {
            "parties": ["Acme Corp", "Globex Inc"],
            "effective_date": "2026-01-01",
            "termination_date": None,
            "monetary_values": [],
            "key_clauses": [],
            "obligations": [],
        }
        return LlmCompletionResult(raw_content=json.dumps(content), model_name=self.model_name)


class FakeEmbeddingProvider:
    provider_name = "fake-embed"
    model_name = "fake-embed-model"

    def embed(self, text: str) -> EmbeddingResult:
        return EmbeddingResult(vector=[0.1, 0.2, 0.3], model_name=self.model_name)


class IngestionIntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.db_engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.db_engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.db_engine)

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
            patch.object(document_service_module, "storage", self.storage),
            patch.object(file_validation_module, "storage", self.storage),
            patch.object(ocr_module, "storage", self.storage),
            patch.object(file_validation_module, "SessionLocal", self.SessionLocal),
            patch.object(ocr_module, "SessionLocal", self.SessionLocal),
            patch.object(extraction_module, "SessionLocal", self.SessionLocal),
            patch.object(embeddings_module, "SessionLocal", self.SessionLocal),
        ]
        for p in self.patches:
            p.start()

        self.trigger_patch = patch.object(
            document_service_module.workflow_client, "trigger_document_workflow", return_value=True
        )
        self.mock_trigger = self.trigger_patch.start()

    def tearDown(self) -> None:
        self.trigger_patch.stop()
        for p in self.patches:
            p.stop()
        app.dependency_overrides.clear()
        self.tmpdir.cleanup()
        Base.metadata.drop_all(self.db_engine)

    def _run_dispatched_chain_synchronously(self, document_id: str) -> None:
        self.assertEqual(validate_file(document_id), "processing")
        self.assertEqual(run_ocr(document_id, engine=FakeOcrEngine()), "complete")
        self.assertEqual(extract_fields(document_id, provider=FakeLlmProvider()), "extracted")
        self.assertEqual(generate_embeddings(document_id, provider=FakeEmbeddingProvider()), "embedded")

    def test_upload_through_full_processing_chain(self) -> None:
        # -- WS-01 -> WS-02: upload lands as metadata and triggers the n8n webhook (WS-04) --
        upload_response = self.client.post(
            "/api/documents",
            files={"file": ("contract.pdf", _sample_pdf(), "application/pdf")},
        )
        self.assertEqual(upload_response.status_code, 201)
        document_id = upload_response.json()["id"]

        self.mock_trigger.assert_called_once()
        self.assertEqual(self.mock_trigger.call_args.args[0], document_id)

        get_response = self.client.get(f"/api/documents/{document_id}")
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.json()["status"], "queued")

        # -- WS-04 -> WS-02: n8n calls the internal endpoint to sequence WS-03's chain --
        fake_task_result = MagicMock(id="chain-task-id")
        with patch("app.api.internal.chain") as mock_chain:
            mock_chain.return_value.apply_async.side_effect = lambda: (
                self._run_dispatched_chain_synchronously(document_id),
                fake_task_result,
            )[1]

            process_response = self.client.post(
                f"/api/internal/documents/{document_id}/process",
                headers={"x-internal-api-key": settings.internal_api_key},
            )

        self.assertEqual(process_response.status_code, 202)
        self.assertEqual(process_response.json()["task_id"], "chain-task-id")

        # -- WS-03 -> WS-02: the pipeline's output is durable and retrievable --
        final_document = self.client.get(f"/api/documents/{document_id}").json()
        self.assertEqual(final_document["status"], "complete")

        ocr_pages = self.client.get(f"/api/documents/{document_id}/ocr").json()
        self.assertEqual(len(ocr_pages), 1)
        self.assertEqual(ocr_pages[0]["extractedText"], "Integration test contract body.")

        extraction = self.client.get(f"/api/documents/{document_id}/extraction").json()
        self.assertEqual(extraction["content"]["parties"], ["Acme Corp", "Globex Inc"])

        chunks = self.client.get(f"/api/documents/{document_id}/chunks").json()
        self.assertGreaterEqual(len(chunks), 1)
        self.assertEqual(chunks[0]["embeddingProvider"], "fake-embed")


if __name__ == "__main__":
    unittest.main()

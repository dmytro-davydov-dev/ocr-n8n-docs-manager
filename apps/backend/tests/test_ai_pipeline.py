import json
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.main import app
from app.models import Base
from app.repositories import document_repository, ocr_repository, chunk_repository
import app.tasks.embeddings as embeddings_module
import app.tasks.extraction as extraction_module
from app.services.embedding_provider import EmbeddingResult
from app.services.llm_provider import LlmCompletionResult
from app.tasks.embeddings import generate_embeddings
from app.tasks.extraction import extract_fields


class FakeLlmProvider:
    provider_name = "fake-llm"
    model_name = "fake-model-1"

    def __init__(self, content: dict | None = None, error: Exception | None = None):
        self._content = (
            content
            if content is not None
            else {
                "parties": ["Acme Corp", "Globex Inc"],
                "effective_date": "2026-01-01",
                "termination_date": None,
                "monetary_values": ["$1,000"],
                "key_clauses": ["confidentiality"],
                "obligations": ["Acme shall pay Globex monthly"],
            }
        )
        self._error = error
        self.calls = 0

    def complete_json(self, *, system_prompt: str, user_content: str) -> LlmCompletionResult:
        self.calls += 1
        if self._error is not None:
            raise self._error
        return LlmCompletionResult(raw_content=json.dumps(self._content), model_name=self.model_name)


class FakeEmbeddingProvider:
    provider_name = "fake-embed"
    model_name = "fake-embed-model-1"

    def __init__(self, error: Exception | None = None, fail_after: int | None = None):
        self._error = error
        self._fail_after = fail_after
        self.calls = 0

    def embed(self, text: str) -> EmbeddingResult:
        self.calls += 1
        if self._error is not None and (self._fail_after is None or self.calls > self._fail_after):
            raise self._error
        return EmbeddingResult(vector=[0.1, 0.2, 0.3], model_name=self.model_name)


class AiPipelineTest(unittest.TestCase):
    _STATUS_PATH = {
        "uploaded": [],
        "queued": ["queued"],
        "processing": ["queued", "processing"],
        "complete": ["queued", "processing", "complete"],
        "failed": ["queued", "failed"],
    }

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

        self.session_local_patches = [
            patch.object(extraction_module, "SessionLocal", self.SessionLocal),
            patch.object(embeddings_module, "SessionLocal", self.SessionLocal),
        ]
        for p in self.session_local_patches:
            p.start()

    def tearDown(self) -> None:
        for p in self.session_local_patches:
            p.stop()
        app.dependency_overrides.clear()
        Base.metadata.drop_all(self.engine)

    def _make_document(self, status: str, page_texts: list[str] | None = None) -> str:
        db = self.SessionLocal()
        try:
            document = document_repository.create(
                db,
                document_id="doc-1",
                filename="contract.pdf",
                content_type="application/pdf",
                size_bytes=100,
                content_hash="hash",
                storage_path="/documents/doc-1/contract.pdf",
                actor="test",
            )
            for target in self._STATUS_PATH[status]:
                document = document_repository.update_status(db, document, new_status=target, actor="test")

            for i, text in enumerate(page_texts or [], start=1):
                ocr_repository.upsert_page(
                    db,
                    document_id=document.id,
                    page_number=i,
                    extracted_text=text,
                    confidence_score=0.9,
                    ocr_engine_version="fake:1",
                )
            db.commit()
            return document.id
        finally:
            db.close()

    # -- extract_fields ---------------------------------------------------

    def test_extract_fields_persists_result_and_records_versions(self) -> None:
        document_id = self._make_document("complete", page_texts=["This is a contract between parties."])
        fake_provider = FakeLlmProvider()

        result = extract_fields(document_id, provider=fake_provider)

        self.assertEqual(result, "extracted")
        self.assertEqual(fake_provider.calls, 1)

        response = self.client.get(f"/api/documents/{document_id}/extraction")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["documentId"], document_id)
        self.assertEqual(body["content"]["parties"], ["Acme Corp", "Globex Inc"])
        self.assertEqual(body["promptId"], "contract_extraction")
        self.assertEqual(body["promptVersion"], "v1")
        self.assertEqual(body["modelProvider"], "fake-llm")
        self.assertEqual(body["modelName"], "fake-model-1")
        self.assertAlmostEqual(body["confidenceScore"], 0.9)

    def test_extract_fields_skips_when_document_not_complete(self) -> None:
        document_id = self._make_document("processing", page_texts=["Some text"])

        result = extract_fields(document_id, provider=FakeLlmProvider())

        self.assertEqual(result, "processing")
        response = self.client.get(f"/api/documents/{document_id}/extraction")
        self.assertEqual(response.status_code, 404)

    def test_extract_fields_is_idempotent_for_same_prompt_version(self) -> None:
        document_id = self._make_document("complete", page_texts=["Some contract text"])

        first_provider = FakeLlmProvider()
        extract_fields(document_id, provider=first_provider)

        second_provider = FakeLlmProvider()
        result = extract_fields(document_id, provider=second_provider)

        self.assertEqual(result, "already_extracted")
        self.assertEqual(second_provider.calls, 0)

    def test_extract_fields_schema_validation_failure_is_terminal(self) -> None:
        document_id = self._make_document("complete", page_texts=["Some contract text"])
        bad_provider = FakeLlmProvider(content={"parties": "not-a-list"})

        result = extract_fields(document_id, provider=bad_provider)

        self.assertEqual(result, "validation_failed")
        response = self.client.get(f"/api/documents/{document_id}/extraction")
        self.assertEqual(response.status_code, 404)

    def test_extract_fields_retries_on_transient_llm_failure(self) -> None:
        document_id = self._make_document("complete", page_texts=["Some contract text"])
        flaky_provider = FakeLlmProvider(error=TimeoutError("llm down"))

        # See test_ocr_pipeline.py: calling the task directly makes
        # self.retry() re-raise the original exception (no real request to
        # reschedule), which still confirms the retry path was taken.
        with self.assertRaises(TimeoutError):
            extract_fields(document_id, provider=flaky_provider)

        response = self.client.get(f"/api/documents/{document_id}/extraction")
        self.assertEqual(response.status_code, 404)

    # -- generate_embeddings ------------------------------------------------

    def test_generate_embeddings_persists_chunks(self) -> None:
        document_id = self._make_document(
            "complete", page_texts=["First page text here.", "Second page text here."]
        )
        fake_provider = FakeEmbeddingProvider()

        result = generate_embeddings(document_id, provider=fake_provider)

        self.assertEqual(result, "embedded")
        self.assertEqual(fake_provider.calls, 2)

        response = self.client.get(f"/api/documents/{document_id}/chunks")
        self.assertEqual(response.status_code, 200)
        chunks = response.json()
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0]["pageNumber"], 1)
        self.assertEqual(chunks[1]["pageNumber"], 2)
        self.assertEqual(chunks[0]["embeddingProvider"], "fake-embed")
        self.assertEqual(chunks[0]["embeddingModel"], "fake-embed-model-1")

    def test_generate_embeddings_skips_when_document_not_complete(self) -> None:
        document_id = self._make_document("queued", page_texts=["text"])

        result = generate_embeddings(document_id, provider=FakeEmbeddingProvider())

        self.assertEqual(result, "queued")

    def test_generate_embeddings_retries_without_losing_prior_chunks(self) -> None:
        document_id = self._make_document(
            "complete", page_texts=["First page text here.", "Second page text here."]
        )
        flaky_provider = FakeEmbeddingProvider(error=TimeoutError("embedding provider down"), fail_after=1)

        with self.assertRaises(TimeoutError):
            generate_embeddings(document_id, provider=flaky_provider)

        response = self.client.get(f"/api/documents/{document_id}/chunks")
        chunks = response.json()
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0]["pageNumber"], 1)

    def test_generate_embeddings_drops_stale_trailing_chunks(self) -> None:
        document_id = self._make_document("complete", page_texts=["Only page text."])

        db = self.SessionLocal()
        chunk_repository.upsert_chunk(
            db,
            document_id=document_id,
            chunk_index=5,
            page_number=1,
            start_offset=0,
            end_offset=4,
            text="stale",
            token_count=1,
            embedding=[0.0],
            embedding_provider="old-provider",
            embedding_model="old-model",
        )
        db.commit()
        db.close()

        generate_embeddings(document_id, provider=FakeEmbeddingProvider())

        response = self.client.get(f"/api/documents/{document_id}/chunks")
        chunks = response.json()
        self.assertEqual(len(chunks), 1)
        self.assertNotEqual(chunks[0]["text"], "stale")


if __name__ == "__main__":
    unittest.main()

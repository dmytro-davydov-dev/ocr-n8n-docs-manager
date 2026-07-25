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
from app.repositories import document_repository, ocr_repository, review_repository
from app.services import rag_service, search_service
from app.services.embedding_provider import EmbeddingResult
from app.services.llm_provider import LlmCompletionResult
from app.tasks.embeddings import generate_embeddings
import app.tasks.embeddings as embeddings_module


class FakeEmbeddingProvider:
    """Returns a fixed vector for every text: keeps the vector-similarity
    signal a constant across chunks in these tests, so ranking is driven by
    the keyword signal and stays deterministic without a real embedding
    model."""

    provider_name = "fake-embed"
    model_name = "fake-embed-model-1"

    def embed(self, text: str) -> EmbeddingResult:
        return EmbeddingResult(vector=[1.0, 0.0, 0.0], model_name=self.model_name)


class FakeLlmProvider:
    provider_name = "fake-llm"
    model_name = "fake-llm-model-1"

    def __init__(self, answer: str = "The termination notice period is 30 days."):
        self._answer = answer
        self.last_user_content: str | None = None

    def complete_json(self, *, system_prompt: str, user_content: str) -> LlmCompletionResult:
        self.last_user_content = user_content
        return LlmCompletionResult(raw_content=json.dumps({"answer": self._answer}), model_name=self.model_name)


class SearchAndChatTest(unittest.TestCase):
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
        self.embeddings_patch = patch.object(embeddings_module, "SessionLocal", self.SessionLocal)
        self.embeddings_patch.start()

    def tearDown(self) -> None:
        self.embeddings_patch.stop()
        app.dependency_overrides.clear()
        Base.metadata.drop_all(self.engine)

    def _make_document(self, document_id: str, page_texts: list[str]) -> None:
        db = self.SessionLocal()
        try:
            document = document_repository.create(
                db,
                document_id=document_id,
                filename="contract.pdf",
                content_type="application/pdf",
                size_bytes=100,
                content_hash=f"hash-{document_id}",
                storage_path=f"/documents/{document_id}/contract.pdf",
                actor="test",
            )
            for target in ("queued", "processing", "complete"):
                document = document_repository.update_status(db, document, new_status=target, actor="test")
            for i, text in enumerate(page_texts, start=1):
                ocr_repository.upsert_page(
                    db,
                    document_id=document.id,
                    page_number=i,
                    extracted_text=text,
                    confidence_score=0.9,
                    ocr_engine_version="fake:1",
                )
            db.commit()
        finally:
            db.close()

        generate_embeddings(document_id, provider=FakeEmbeddingProvider())

    def _approve_review(self, document_id: str) -> None:
        db = self.SessionLocal()
        try:
            review = review_repository.create(db, document_id=document_id, actor="test", content={"parties": []})
            review = review_repository.transition(
                db, review, new_status="in_review", expected_version=1, actor="test"
            )
            review_repository.transition(db, review, new_status="approved", expected_version=2, actor="test")
        finally:
            db.close()

    def _make_approved_document(self, document_id: str, page_texts: list[str]) -> None:
        self._make_document(document_id, page_texts)
        self._approve_review(document_id)

    # -- search_service -----------------------------------------------------

    def test_hybrid_search_ranks_matching_chunk_first(self) -> None:
        self._make_approved_document(
            "doc-1",
            [
                "This agreement may be terminated with 30 days written notice.",
                "The parties agree to keep all information confidential.",
            ],
        )

        db = self.SessionLocal()
        try:
            hits = search_service.hybrid_search(
                db, query="termination notice", limit=5, embedding_provider=FakeEmbeddingProvider()
            )
        finally:
            db.close()

        self.assertTrue(hits)
        self.assertIn("notice", hits[0].chunk.text)

    def test_search_excludes_chunks_from_unapproved_documents(self) -> None:
        self._make_document("doc-2", ["Confidential termination clause and notice period."])
        # No review created/approved for doc-2 -- FR-501 gate.

        db = self.SessionLocal()
        try:
            hits = search_service.hybrid_search(
                db, query="termination", limit=5, embedding_provider=FakeEmbeddingProvider()
            )
        finally:
            db.close()

        self.assertEqual(hits, [])

    # -- HTTP endpoints -------------------------------------------------------

    def test_search_endpoint_returns_ranked_results(self) -> None:
        self._make_approved_document(
            "doc-3", ["This agreement may be terminated with 30 days written notice."]
        )

        with patch.object(search_service, "get_embedding_provider", lambda: FakeEmbeddingProvider()):
            response = self.client.get("/api/search", params={"q": "termination notice"})

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body), 1)
        self.assertEqual(body[0]["documentId"], "doc-3")
        self.assertIn("notice", body[0]["snippet"])

    def test_search_endpoint_empty_when_nothing_approved(self) -> None:
        self._make_document("doc-4", ["Some unapproved clause text."])

        with patch.object(search_service, "get_embedding_provider", lambda: FakeEmbeddingProvider()):
            response = self.client.get("/api/search", params={"q": "clause"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_chat_endpoint_returns_answer_with_citations(self) -> None:
        self._make_approved_document(
            "doc-5", ["This agreement may be terminated with 30 days written notice."]
        )

        with (
            patch.object(search_service, "get_embedding_provider", lambda: FakeEmbeddingProvider()),
            patch.object(rag_service, "get_llm_provider", lambda: FakeLlmProvider()),
        ):
            response = self.client.post(
                "/api/chat", json={"question": "How much notice is required to terminate?"}
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["answer"], "The termination notice period is 30 days.")
        self.assertEqual(len(body["citations"]), 1)
        self.assertEqual(body["citations"][0]["documentId"], "doc-5")
        self.assertEqual(body["model"], "fake-llm-model-1")

    def test_chat_endpoint_404s_when_nothing_indexed(self) -> None:
        with patch.object(search_service, "get_embedding_provider", lambda: FakeEmbeddingProvider()):
            response = self.client.post("/api/chat", json={"question": "anything?"})

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()

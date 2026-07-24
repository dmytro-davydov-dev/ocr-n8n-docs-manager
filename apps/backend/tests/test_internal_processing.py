import tempfile
import unittest
from unittest.mock import MagicMock, patch

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


class InternalProcessingTriggerTest(unittest.TestCase):
    """WS-04: n8n's only path into Celery is this internal endpoint (ADR-009)
    -- it never talks to the broker directly. Covers the contract n8n's
    upload workflow depends on: auth, 404 on unknown documents, and a
    dispatched task id on success."""

    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        def override_get_db():
            db = TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db

        self.tmpdir = tempfile.TemporaryDirectory()
        self.storage_patch = patch.object(
            document_service_module, "storage", LocalDocumentStorage(self.tmpdir.name)
        )
        self.storage_patch.start()

        self.trigger_patch = patch(
            "app.services.document_service.workflow_client.trigger_document_workflow",
            return_value=True,
        )
        self.trigger_patch.start()

        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.trigger_patch.stop()
        self.storage_patch.stop()
        self.tmpdir.cleanup()
        Base.metadata.drop_all(self.engine)

    def _upload(self) -> str:
        response = self.client.post(
            "/api/documents",
            files={"file": ("contract.pdf", b"%PDF-1.4 test", "application/pdf")},
        )
        return response.json()["id"]

    def test_process_requires_internal_api_key(self) -> None:
        document_id = self._upload()

        response = self.client.post(f"/api/internal/documents/{document_id}/process")

        self.assertEqual(response.status_code, 401)

    def test_process_returns_404_for_unknown_document(self) -> None:
        response = self.client.post(
            "/api/internal/documents/does-not-exist/process",
            headers={"x-internal-api-key": settings.internal_api_key},
        )

        self.assertEqual(response.status_code, 404)

    def test_process_dispatches_pipeline_chain(self) -> None:
        document_id = self._upload()

        fake_result = MagicMock(id="task-123")
        with patch("app.api.internal.chain") as mock_chain:
            mock_chain.return_value.apply_async.return_value = fake_result

            response = self.client.post(
                f"/api/internal/documents/{document_id}/process",
                headers={"x-internal-api-key": settings.internal_api_key},
            )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(
            response.json(), {"document_id": document_id, "task_id": "task-123"}
        )
        mock_chain.assert_called_once()
        mock_chain.return_value.apply_async.assert_called_once()


if __name__ == "__main__":
    unittest.main()

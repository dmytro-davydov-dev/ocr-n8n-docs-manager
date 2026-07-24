import tempfile
import unittest
from unittest.mock import patch

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


class DocumentsApiTest(unittest.TestCase):
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

    def _upload(self, filename="contract.pdf", content=b"%PDF-1.4 test", content_type="application/pdf"):
        return self.client.post(
            "/api/documents",
            files={"file": (filename, content, content_type)},
        )

    def test_upload_persists_and_triggers_workflow(self) -> None:
        response = self._upload()

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["filename"], "contract.pdf")
        self.assertEqual(body["status"], "queued")
        self.assertEqual(body["sizeBytes"], len(b"%PDF-1.4 test"))
        self.assertIn("id", body)

    def test_upload_rejects_unsupported_content_type(self) -> None:
        response = self._upload(filename="notes.txt", content=b"hello", content_type="text/plain")

        self.assertEqual(response.status_code, 422)

    def test_upload_failure_to_trigger_workflow_surfaces_as_failed(self) -> None:
        with patch(
            "app.services.document_service.workflow_client.trigger_document_workflow",
            return_value=False,
        ):
            response = self._upload()

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["status"], "failed")
        self.assertEqual(body["errorMessage"], "Failed to trigger processing workflow")

    def test_list_and_get_document(self) -> None:
        uploaded = self._upload().json()

        list_response = self.client.get("/api/documents")
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.json()), 1)

        get_response = self.client.get(f"/api/documents/{uploaded['id']}")
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.json()["id"], uploaded["id"])

    def test_get_unknown_document_returns_404(self) -> None:
        response = self.client.get("/api/documents/does-not-exist")
        self.assertEqual(response.status_code, 404)

    def test_get_document_file_returns_bytes(self) -> None:
        uploaded = self._upload(content=b"%PDF-1.4 filebytes").json()

        response = self.client.get(f"/api/documents/{uploaded['id']}/file")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"%PDF-1.4 filebytes")
        self.assertEqual(response.headers["content-type"], "application/pdf")

    def test_internal_status_update_requires_api_key(self) -> None:
        uploaded = self._upload().json()

        response = self.client.patch(
            f"/api/internal/documents/{uploaded['id']}/status",
            json={"status": "processing"},
        )

        self.assertEqual(response.status_code, 401)

    def test_internal_status_update_advances_lifecycle(self) -> None:
        uploaded = self._upload().json()
        headers = {"x-internal-api-key": settings.internal_api_key}

        processing = self.client.patch(
            f"/api/internal/documents/{uploaded['id']}/status",
            json={"status": "processing"},
            headers=headers,
        )
        self.assertEqual(processing.status_code, 200)
        self.assertEqual(processing.json()["status"], "processing")

        complete = self.client.patch(
            f"/api/internal/documents/{uploaded['id']}/status",
            json={"status": "complete"},
            headers=headers,
        )
        self.assertEqual(complete.status_code, 200)
        self.assertEqual(complete.json()["status"], "complete")

    def test_internal_status_update_rejects_illegal_transition(self) -> None:
        uploaded = self._upload().json()
        headers = {"x-internal-api-key": settings.internal_api_key}

        response = self.client.patch(
            f"/api/internal/documents/{uploaded['id']}/status",
            json={"status": "complete"},
            headers=headers,
        )

        self.assertEqual(response.status_code, 409)


if __name__ == "__main__":
    unittest.main()

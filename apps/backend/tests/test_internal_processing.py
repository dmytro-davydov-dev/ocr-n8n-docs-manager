import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, update
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import get_db
from app.core.storage import LocalDocumentStorage
from app.main import app
from app.models import Base
from app.models.document import Document
from app.repositories import document_repository
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

    def test_reprocess_requires_internal_api_key(self) -> None:
        document_id = self._upload()

        response = self.client.post(f"/api/internal/documents/{document_id}/reprocess")

        self.assertEqual(response.status_code, 401)

    def test_reprocess_returns_404_for_unknown_document(self) -> None:
        response = self.client.post(
            "/api/internal/documents/does-not-exist/reprocess",
            headers={"x-internal-api-key": settings.internal_api_key},
        )

        self.assertEqual(response.status_code, 404)

    def test_reprocess_resets_failed_document_to_queued_and_redispatches(self) -> None:
        document_id = self._upload()
        db = next(app.dependency_overrides[get_db]())
        try:
            document = document_repository.get(db, document_id)
            for target in ("queued", "failed"):
                document = document_repository.update_status(db, document, new_status=target, actor="test")
        finally:
            db.close()

        fake_result = MagicMock(id="task-456")
        with patch("app.api.internal.chain") as mock_chain:
            mock_chain.return_value.apply_async.return_value = fake_result

            response = self.client.post(
                f"/api/internal/documents/{document_id}/reprocess",
                headers={"x-internal-api-key": settings.internal_api_key},
            )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.json(), {"document_id": document_id, "task_id": "task-456"})
        mock_chain.return_value.apply_async.assert_called_once()

        db = next(app.dependency_overrides[get_db]())
        try:
            self.assertEqual(document_repository.get(db, document_id).status, "queued")
        finally:
            db.close()

    def test_reprocess_rejects_document_mid_pipeline(self) -> None:
        document_id = self._upload()
        db = next(app.dependency_overrides[get_db]())
        try:
            document = document_repository.get(db, document_id)
            document_repository.update_status(db, document, new_status="queued", actor="test")
        finally:
            db.close()

        response = self.client.post(
            f"/api/internal/documents/{document_id}/reprocess",
            headers={"x-internal-api-key": settings.internal_api_key},
        )

        self.assertEqual(response.status_code, 409)

    def test_reprocess_unsticks_a_stale_processing_document(self) -> None:
        """A document wedged in 'processing' past the stuck threshold (e.g.
        a task that hit its Celery time limit -- see app/tasks/ocr.py) can
        be force-reprocessed by an operator, unlike one still genuinely
        mid-pipeline (test_reprocess_rejects_document_mid_pipeline)."""
        document_id = self._upload()
        db = next(app.dependency_overrides[get_db]())
        try:
            document = document_repository.get(db, document_id)
            document_repository.update_status(db, document, new_status="queued", actor="test")
            document_repository.update_status(db, document, new_status="processing", actor="test")

            stale_at = datetime.now(timezone.utc) - timedelta(
                minutes=settings.document_stuck_threshold_minutes + 1
            )
            db.execute(update(Document).where(Document.id == document_id).values(updated_at=stale_at))
            db.commit()
        finally:
            db.close()

        fake_result = MagicMock(id="task-unstick")
        with patch("app.api.internal.chain") as mock_chain:
            mock_chain.return_value.apply_async.return_value = fake_result

            response = self.client.post(
                f"/api/internal/documents/{document_id}/reprocess",
                headers={"x-internal-api-key": settings.internal_api_key},
            )

        self.assertEqual(response.status_code, 202)
        mock_chain.return_value.apply_async.assert_called_once()

        db = next(app.dependency_overrides[get_db]())
        try:
            self.assertEqual(document_repository.get(db, document_id).status, "queued")
        finally:
            db.close()

    def test_reprocess_resets_retry_count(self) -> None:
        document_id = self._upload()
        db = next(app.dependency_overrides[get_db]())
        try:
            document = document_repository.get(db, document_id)
            for target in ("queued", "failed"):
                document = document_repository.update_status(db, document, new_status=target, actor="test")
            document_repository.increment_retry_count(db, document)
            document_repository.increment_retry_count(db, document)
        finally:
            db.close()

        with patch("app.api.internal.chain") as mock_chain:
            mock_chain.return_value.apply_async.return_value = MagicMock(id="task-reset")
            self.client.post(
                f"/api/internal/documents/{document_id}/reprocess",
                headers={"x-internal-api-key": settings.internal_api_key},
            )

        db = next(app.dependency_overrides[get_db]())
        try:
            self.assertEqual(document_repository.get(db, document_id).retry_count, 0)
        finally:
            db.close()


class InternalAutoRetryTest(unittest.TestCase):
    """Blocker: "no automated recovery for stuck/failed documents" -- the n8n
    watchdog now drives this endpoint instead of only surfacing failures."""

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

    def _upload_failed_document(self) -> str:
        response = self.client.post(
            "/api/documents",
            files={"file": ("contract.pdf", b"%PDF-1.4 test", "application/pdf")},
        )
        document_id = response.json()["id"]
        db = next(app.dependency_overrides[get_db]())
        try:
            document = document_repository.get(db, document_id)
            for target in ("queued", "failed"):
                document = document_repository.update_status(db, document, new_status=target, actor="test")
        finally:
            db.close()
        return document_id

    def test_auto_retry_requires_internal_api_key(self) -> None:
        document_id = self._upload_failed_document()

        response = self.client.post(f"/api/internal/documents/{document_id}/auto-retry")

        self.assertEqual(response.status_code, 401)

    def test_auto_retry_returns_404_for_unknown_document(self) -> None:
        response = self.client.post(
            "/api/internal/documents/does-not-exist/auto-retry",
            headers={"x-internal-api-key": settings.internal_api_key},
        )

        self.assertEqual(response.status_code, 404)

    def test_auto_retry_rejects_non_failed_document(self) -> None:
        response = self.client.post(
            "/api/documents",
            files={"file": ("contract.pdf", b"%PDF-1.4 test", "application/pdf")},
        )
        document_id = response.json()["id"]

        response = self.client.post(
            f"/api/internal/documents/{document_id}/auto-retry",
            headers={"x-internal-api-key": settings.internal_api_key},
        )

        self.assertEqual(response.status_code, 409)

    def test_auto_retry_dispatches_and_increments_retry_count(self) -> None:
        document_id = self._upload_failed_document()

        fake_result = MagicMock(id="task-auto-1")
        with patch("app.api.internal.chain") as mock_chain:
            mock_chain.return_value.apply_async.return_value = fake_result

            response = self.client.post(
                f"/api/internal/documents/{document_id}/auto-retry",
                headers={"x-internal-api-key": settings.internal_api_key},
            )

        self.assertEqual(response.status_code, 202)
        self.assertEqual(
            response.json(),
            {"document_id": document_id, "task_id": "task-auto-1", "retry_count": 1},
        )

        db = next(app.dependency_overrides[get_db]())
        try:
            document = document_repository.get(db, document_id)
            self.assertEqual(document.status, "queued")
            self.assertEqual(document.retry_count, 1)
        finally:
            db.close()

    def test_auto_retry_stops_once_budget_exhausted(self) -> None:
        document_id = self._upload_failed_document()

        with patch("app.api.internal.chain") as mock_chain:
            mock_chain.return_value.apply_async.return_value = MagicMock(id="task-x")

            for _ in range(settings.document_auto_retry_max):
                # Each successful auto-retry dispatches and moves the
                # document to 'queued'; simulate the pipeline failing again
                # before the next watchdog sweep.
                response = self.client.post(
                    f"/api/internal/documents/{document_id}/auto-retry",
                    headers={"x-internal-api-key": settings.internal_api_key},
                )
                self.assertEqual(response.status_code, 202)

                db = next(app.dependency_overrides[get_db]())
                try:
                    document = document_repository.get(db, document_id)
                    document_repository.update_status(
                        db, document, new_status="failed", actor="test"
                    )
                finally:
                    db.close()

            response = self.client.post(
                f"/api/internal/documents/{document_id}/auto-retry",
                headers={"x-internal-api-key": settings.internal_api_key},
            )

        self.assertEqual(response.status_code, 409)
        self.assertIn("exhausted", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()

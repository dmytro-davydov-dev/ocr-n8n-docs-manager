import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.storage import LocalDocumentStorage
from app.main import app
from app.models import Base
import app.services.document_service as document_service_module


class ReviewsApiTest(unittest.TestCase):
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

    def _complete_document(self) -> str:
        """Upload a document and drive it (via the internal callback n8n
        would use) all the way to `complete`, since review only starts once
        processing is done."""
        uploaded = self.client.post(
            "/api/documents",
            files={"file": ("contract.pdf", b"%PDF-1.4 test", "application/pdf")},
        ).json()
        headers = {"x-internal-api-key": "change-me"}
        self.client.patch(
            f"/api/internal/documents/{uploaded['id']}/status",
            json={"status": "processing"},
            headers=headers,
        )
        self.client.patch(
            f"/api/internal/documents/{uploaded['id']}/status",
            json={"status": "complete"},
            headers=headers,
        )
        return uploaded["id"]

    def test_create_review_requires_completed_document(self) -> None:
        uploaded = self.client.post(
            "/api/documents",
            files={"file": ("contract.pdf", b"%PDF-1.4 test", "application/pdf")},
        ).json()

        response = self.client.post(f"/api/documents/{uploaded['id']}/review", json={"content": {}})

        self.assertEqual(response.status_code, 409)

    def test_create_review_succeeds_once_complete(self) -> None:
        document_id = self._complete_document()

        response = self.client.post(
            f"/api/documents/{document_id}/review",
            json={"content": {"clause_1": "original AI text"}},
        )

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["status"], "draft_review")
        self.assertEqual(body["version"], 1)
        self.assertEqual(body["content"], {"clause_1": "original AI text"})

    def test_create_review_twice_conflicts(self) -> None:
        document_id = self._complete_document()
        self.client.post(f"/api/documents/{document_id}/review", json={"content": {}})

        response = self.client.post(f"/api/documents/{document_id}/review", json={"content": {}})

        self.assertEqual(response.status_code, 409)

    def test_save_draft_bumps_version_and_preserves_history(self) -> None:
        document_id = self._complete_document()
        self.client.post(
            f"/api/documents/{document_id}/review", json={"content": {"clause_1": "original"}}
        )

        response = self.client.patch(
            f"/api/documents/{document_id}/review",
            json={"content": {"clause_1": "edited by user"}, "expectedVersion": 1},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["version"], 2)
        self.assertEqual(body["content"], {"clause_1": "edited by user"})

        history = self.client.get(f"/api/documents/{document_id}/review/history").json()
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["version"], 1)
        self.assertEqual(history[0]["content"], {"clause_1": "original"})
        self.assertEqual(history[1]["version"], 2)
        self.assertEqual(history[1]["content"], {"clause_1": "edited by user"})

    def test_save_draft_with_stale_version_conflicts(self) -> None:
        document_id = self._complete_document()
        self.client.post(f"/api/documents/{document_id}/review", json={"content": {"a": 1}})

        response = self.client.patch(
            f"/api/documents/{document_id}/review",
            json={"content": {"a": 2}, "expectedVersion": 99},
        )

        self.assertEqual(response.status_code, 412)

    def test_full_approval_lifecycle(self) -> None:
        document_id = self._complete_document()
        self.client.post(f"/api/documents/{document_id}/review", json={"content": {"a": 1}})

        submitted = self.client.post(
            f"/api/documents/{document_id}/review/submit", json={"expectedVersion": 1}
        )
        self.assertEqual(submitted.status_code, 200)
        self.assertEqual(submitted.json()["status"], "in_review")

        approved = self.client.post(
            f"/api/documents/{document_id}/review/approve", json={"expectedVersion": 2}
        )
        self.assertEqual(approved.status_code, 200)
        self.assertEqual(approved.json()["status"], "approved")

        archived = self.client.post(
            f"/api/documents/{document_id}/review/archive", json={"expectedVersion": 3}
        )
        self.assertEqual(archived.status_code, 200)
        self.assertEqual(archived.json()["status"], "archived")

    def test_cannot_approve_directly_from_draft(self) -> None:
        document_id = self._complete_document()
        self.client.post(f"/api/documents/{document_id}/review", json={"content": {"a": 1}})

        response = self.client.post(
            f"/api/documents/{document_id}/review/approve", json={"expectedVersion": 1}
        )

        self.assertEqual(response.status_code, 409)

    def test_cannot_approve_empty_content(self) -> None:
        document_id = self._complete_document()
        self.client.post(f"/api/documents/{document_id}/review", json={"content": {}})
        self.client.post(f"/api/documents/{document_id}/review/submit", json={"expectedVersion": 1})

        response = self.client.post(
            f"/api/documents/{document_id}/review/approve", json={"expectedVersion": 2}
        )

        self.assertEqual(response.status_code, 422)

    def test_reject_requires_reason_and_returns_to_draft(self) -> None:
        document_id = self._complete_document()
        self.client.post(f"/api/documents/{document_id}/review", json={"content": {"a": 1}})
        self.client.post(f"/api/documents/{document_id}/review/submit", json={"expectedVersion": 1})

        rejected = self.client.post(
            f"/api/documents/{document_id}/review/reject",
            json={"expectedVersion": 2, "reason": "missing indemnity clause"},
        )
        self.assertEqual(rejected.status_code, 200)
        self.assertEqual(rejected.json()["status"], "rejected")
        self.assertEqual(rejected.json()["rejectionReason"], "missing indemnity clause")

        # rejected -> in_review is not legal; only draft_review/archived are.
        back_to_in_review = self.client.post(
            f"/api/documents/{document_id}/review/submit", json={"expectedVersion": 3}
        )
        self.assertEqual(back_to_in_review.status_code, 409)

        revised = self.client.post(
            f"/api/documents/{document_id}/review/revise", json={"expectedVersion": 3}
        )
        self.assertEqual(revised.status_code, 200)
        self.assertEqual(revised.json()["status"], "draft_review")
        self.assertIsNone(revised.json()["rejectionReason"])

        edited = self.client.patch(
            f"/api/documents/{document_id}/review",
            json={"content": {"a": 2}, "expectedVersion": 4},
        )
        self.assertEqual(edited.status_code, 200)
        self.assertEqual(edited.json()["content"], {"a": 2})

    def test_review_mutations_are_audit_logged(self) -> None:
        from app.models.audit_log import AuditLog

        document_id = self._complete_document()
        self.client.post(f"/api/documents/{document_id}/review", json={"content": {"a": 1}})
        self.client.patch(
            f"/api/documents/{document_id}/review",
            json={"content": {"a": 2}, "expectedVersion": 1},
        )

        session = sessionmaker(bind=self.engine)()
        try:
            actions = [
                row.action
                for row in session.query(AuditLog).filter(AuditLog.entity_type == "review").all()
            ]
        finally:
            session.close()

        self.assertIn("created", actions)
        self.assertIn("draft_saved", actions)

    def test_get_unknown_review_returns_404(self) -> None:
        document_id = self._complete_document()
        response = self.client.get(f"/api/documents/{document_id}/review")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()

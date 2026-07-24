"""Phase 1 deliverable (WS-03): a Celery-based inspection pass on top of the
synchronous checks `document_service._validate` already runs at upload time
(content-type/size). This task opens the stored bytes with PyMuPDF to catch
truncated/corrupt PDFs that pass a content-type check but cannot actually be
processed downstream (ADR-008: "validating or inspecting uploaded files").
"""

import logging

from app.celery_app import celery_app
from app.core.database import SessionLocal
from app.core.storage import storage
from app.repositories import document_repository

logger = logging.getLogger("app.tasks.file_validation")


class TerminalValidationError(Exception):
    """A validation failure that will not resolve on retry (ADR-008)."""


def _inspect_pdf(content: bytes) -> None:
    if not content.startswith(b"%PDF-"):
        raise TerminalValidationError("File is not a valid PDF (missing %PDF- header)")

    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise TerminalValidationError(
            "PDF inspection dependency (PyMuPDF) is not installed"
        ) from None

    try:
        with fitz.open(stream=content, filetype="pdf") as pdf:
            if pdf.page_count == 0:
                raise TerminalValidationError("PDF has zero pages")
    except TerminalValidationError:
        raise
    except Exception as exc:  # PyMuPDF raises its own RuntimeError/ValueError variants
        raise TerminalValidationError(f"PDF failed to parse: {exc}") from exc


@celery_app.task(name="documents.validate_file", bind=True, max_retries=3, default_retry_delay=10)
def validate_file(self, document_id: str) -> str:
    """Identifiers only in the payload (ADR-008) — the file itself is loaded
    from shared storage. Idempotent: only acts on documents in 'queued';
    duplicate delivery after a document has already moved on is a no-op."""
    db = SessionLocal()
    try:
        document = document_repository.get(db, document_id)
        if document is None:
            logger.warning("validate_file: document %s not found", document_id)
            return "not_found"

        if document.status != "queued":
            logger.info(
                "validate_file: document %s already in status '%s', skipping",
                document_id,
                document.status,
            )
            return document.status

        try:
            content = storage.read(document.storage_path)
        except OSError as exc:
            logger.warning("validate_file: transient storage read failure for %s: %s", document_id, exc)
            raise self.retry(exc=exc)

        try:
            _inspect_pdf(content)
        except TerminalValidationError as exc:
            logger.info("validate_file: document %s failed validation: %s", document_id, exc)
            document_repository.update_status(
                db,
                document,
                new_status="failed",
                actor="celery:validate_file",
                error_message=str(exc),
            )
            return "failed"

        document_repository.update_status(
            db, document, new_status="processing", actor="celery:validate_file"
        )
        return "processing"
    finally:
        db.close()

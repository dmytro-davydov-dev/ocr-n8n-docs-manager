import logging
import uuid

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.storage import storage
from app.models.document import Document
from app.repositories import document_repository
from app.services import workflow_client

logger = logging.getLogger("app.document_service")


class UnsupportedFileType(ValueError):
    pass


class FileTooLarge(ValueError):
    pass


def _validate(filename: str, content_type: str, size_bytes: int) -> None:
    if content_type not in settings.allowed_upload_content_types:
        raise UnsupportedFileType(
            f"Unsupported content type '{content_type}'. Allowed: {settings.allowed_upload_content_types}"
        )
    if size_bytes > settings.max_upload_size_bytes:
        raise FileTooLarge(
            f"File '{filename}' ({size_bytes} bytes) exceeds the {settings.max_upload_size_bytes}-byte limit"
        )
    if size_bytes == 0:
        raise UnsupportedFileType(f"File '{filename}' is empty")


def ingest_document(db: Session, *, filename: str, content_type: str, content: bytes, actor: str) -> Document:
    """FR-101-105: validate, persist metadata, store the file, and trigger
    the n8n processing workflow. Runs as one logical unit so a document
    never appears with metadata but no stored bytes.
    """
    _validate(filename, content_type, len(content))

    document_id = str(uuid.uuid4())
    stored = storage.save(document_id, filename, content)

    document = document_repository.create(
        db,
        document_id=document_id,
        filename=filename,
        content_type=content_type,
        size_bytes=stored.size_bytes,
        content_hash=stored.content_hash,
        storage_path=stored.storage_path,
        actor=actor,
    )

    triggered = workflow_client.trigger_document_workflow(document.id)
    if triggered:
        document = document_repository.update_status(
            db, document, new_status="queued", actor="system:workflow_client"
        )
    else:
        document = document_repository.update_status(
            db,
            document,
            new_status="failed",
            actor="system:workflow_client",
            error_message="Failed to trigger processing workflow",
        )

    return document


def get_document_file(document: Document) -> bytes:
    return storage.read(document.storage_path)

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document
from app.repositories import audit_repository

# Legal document-status transitions. Enforced here so no caller can push the
# lifecycle (FR-106) into an inconsistent state via a raw status write.
#
# `complete`/`failed` -> `queued` supports reprocessing (ADR-011 anticipated
# this as a benefit of page-level OCR storage): every downstream pipeline
# task is already idempotent (upsert-by-key, re-checks current status), so
# resetting to `queued` and re-dispatching the same chain is safe and just
# overwrites prior OCR/extraction/chunk rows rather than duplicating them.
#
# `processing`/`queued` -> `queued` is the same reprocess reset applied to a
# document the watchdog flagged as stuck (Progress.md: "processing"/"queued"
# for >15 minutes is a wedged worker/broker problem the watchdog only
# surfaces for a human -- see 02-processing-watchdog.json). Without this edge
# an operator who has confirmed a document is genuinely wedged had no
# supported way to clear it: /reprocess only accepted `complete`/`failed`, so
# a document stuck mid-pipeline could never be reset. The pipeline's tasks
# are idempotent for the same reason `complete`/`failed` -> `queued` is safe.
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "uploaded": {"queued", "failed"},
    "queued": {"processing", "failed"},
    "processing": {"complete", "failed", "queued"},
    "complete": {"queued"},
    "failed": {"queued"},
}


class InvalidStatusTransition(ValueError):
    pass


class DocumentAlreadyArchived(ValueError):
    pass


class DocumentNotArchived(ValueError):
    pass


def create(
    db: Session,
    *,
    document_id: str,
    filename: str,
    content_type: str,
    size_bytes: int,
    content_hash: str,
    storage_path: str,
    actor: str,
) -> Document:
    document = Document(
        id=document_id,
        filename=filename,
        content_type=content_type,
        size_bytes=size_bytes,
        content_hash=content_hash,
        storage_path=storage_path,
        status="uploaded",
    )
    db.add(document)
    db.flush()

    audit_repository.record(
        db,
        entity_type="document",
        entity_id=document.id,
        action="created",
        actor=actor,
        details={"filename": filename, "size_bytes": size_bytes, "content_hash": content_hash},
    )
    db.commit()
    db.refresh(document)
    return document


def get(db: Session, document_id: str) -> Document | None:
    return db.get(Document, document_id)


def list_all(db: Session, *, include_archived: bool = False) -> list[Document]:
    stmt = select(Document).order_by(Document.created_at.desc())
    if not include_archived:
        stmt = stmt.where(Document.archived_at.is_(None))
    return list(db.scalars(stmt).all())


def update_status(
    db: Session,
    document: Document,
    *,
    new_status: str,
    actor: str,
    error_message: str | None = None,
) -> Document:
    allowed = ALLOWED_TRANSITIONS.get(document.status, set())
    if new_status != document.status and new_status not in allowed:
        raise InvalidStatusTransition(
            f"Cannot transition document {document.id} from '{document.status}' to '{new_status}'"
        )

    previous_status = document.status
    document.status = new_status
    document.error_message = error_message
    db.add(document)
    db.flush()

    audit_repository.record(
        db,
        entity_type="document",
        entity_id=document.id,
        action="status_changed",
        actor=actor,
        details={"from": previous_status, "to": new_status, "error_message": error_message},
    )
    db.commit()
    db.refresh(document)
    return document


def archive(db: Session, document: Document, *, actor: str) -> Document:
    """Soft-remove a document from the default list view. Deliberately
    independent of `status`/`ALLOWED_TRANSITIONS`: archiving doesn't change
    where a document is in the processing pipeline, it just hides it, so any
    status (including mid-pipeline) can be archived."""
    if document.archived_at is not None:
        raise DocumentAlreadyArchived(f"Document {document.id} is already archived")

    document.archived_at = datetime.now(timezone.utc)
    db.add(document)
    db.flush()

    audit_repository.record(
        db,
        entity_type="document",
        entity_id=document.id,
        action="archived",
        actor=actor,
        details={"status": document.status},
    )
    db.commit()
    db.refresh(document)
    return document


def unarchive(db: Session, document: Document, *, actor: str) -> Document:
    if document.archived_at is None:
        raise DocumentNotArchived(f"Document {document.id} is not archived")

    document.archived_at = None
    db.add(document)
    db.flush()

    audit_repository.record(
        db,
        entity_type="document",
        entity_id=document.id,
        action="unarchived",
        actor=actor,
        details={"status": document.status},
    )
    db.commit()
    db.refresh(document)
    return document


def reset_retry_count(db: Session, document: Document) -> Document:
    """Called on an explicit operator-triggered reprocess (POST .../reprocess)
    -- a deliberate new attempt starts the auto-retry budget over, distinct
    from the watchdog's automatic ones."""
    document.retry_count = 0
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def increment_retry_count(db: Session, document: Document) -> Document:
    """Called by the watchdog-driven auto-retry path (POST .../auto-retry)
    each time it re-dispatches a `failed` document, so it can stop once
    settings.document_auto_retry_max is reached rather than retrying forever."""
    document.retry_count += 1
    db.add(document)
    db.flush()

    audit_repository.record(
        db,
        entity_type="document",
        entity_id=document.id,
        action="auto_retry",
        actor="n8n:watchdog",
        details={"retry_count": document.retry_count},
    )
    db.commit()
    db.refresh(document)
    return document

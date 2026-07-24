from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document
from app.repositories import audit_repository

# Legal document-status transitions. Enforced here so no caller can push the
# lifecycle (FR-106) into an inconsistent state via a raw status write.
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "uploaded": {"queued", "failed"},
    "queued": {"processing", "failed"},
    "processing": {"complete", "failed"},
    "complete": set(),
    "failed": set(),
}


class InvalidStatusTransition(ValueError):
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


def list_all(db: Session) -> list[Document]:
    stmt = select(Document).order_by(Document.created_at.desc())
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

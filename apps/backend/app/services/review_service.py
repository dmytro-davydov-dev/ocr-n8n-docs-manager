from typing import Any

from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.review import Review
from app.repositories import review_repository


class DocumentNotReady(ValueError):
    pass


def start_review(db: Session, document: Document, *, actor: str, content: dict[str, Any]) -> Review:
    """A review can only start once processing has produced something to
    review (WS-03's OCR/extraction output). Until Phase 2/3 ship, `content`
    is caller-supplied; once extraction exists, this becomes the seed for
    the initial draft (ADR-014: AI Extracted -> Draft Review)."""
    if document.status != "complete":
        raise DocumentNotReady(
            f"Document {document.id} is not ready for review (status: '{document.status}')"
        )
    return review_repository.create(db, document_id=document.id, actor=actor, content=content)

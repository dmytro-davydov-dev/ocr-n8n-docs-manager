from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.extraction import Extraction


def upsert(
    db: Session,
    *,
    document_id: str,
    content: dict[str, Any],
    confidence_score: float,
    prompt_id: str,
    prompt_version: str,
    model_provider: str,
    model_name: str,
) -> Extraction:
    """Idempotent write: re-running extraction for a document (duplicate
    delivery, or an operator-triggered retry after a prompt/model change)
    overwrites the single row for that document instead of accumulating
    duplicates (ADR-008)."""
    existing = db.scalar(select(Extraction).where(Extraction.document_id == document_id))

    now = datetime.now(timezone.utc)
    if existing is not None:
        existing.content = content
        existing.confidence_score = confidence_score
        existing.prompt_id = prompt_id
        existing.prompt_version = prompt_version
        existing.model_provider = model_provider
        existing.model_name = model_name
        existing.processing_timestamp = now
        db.add(existing)
        db.flush()
        return existing

    extraction = Extraction(
        document_id=document_id,
        content=content,
        confidence_score=confidence_score,
        prompt_id=prompt_id,
        prompt_version=prompt_version,
        model_provider=model_provider,
        model_name=model_name,
        processing_timestamp=now,
    )
    db.add(extraction)
    db.flush()
    return extraction


def get_for_document(db: Session, document_id: str) -> Extraction | None:
    return db.scalar(select(Extraction).where(Extraction.document_id == document_id))

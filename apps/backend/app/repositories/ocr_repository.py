from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ocr_page import OcrPage


def upsert_page(
    db: Session,
    *,
    document_id: str,
    page_number: int,
    extracted_text: str,
    confidence_score: float,
    ocr_engine_version: str,
) -> OcrPage:
    """Idempotent write: re-running OCR for a page (duplicate Celery delivery,
    or an operator-triggered retry) overwrites the existing row for that
    (document_id, page_number) instead of accumulating duplicates."""
    existing = db.scalar(
        select(OcrPage).where(
            OcrPage.document_id == document_id, OcrPage.page_number == page_number
        )
    )

    now = datetime.now(timezone.utc)
    if existing is not None:
        existing.extracted_text = extracted_text
        existing.confidence_score = confidence_score
        existing.ocr_engine_version = ocr_engine_version
        existing.processing_timestamp = now
        db.add(existing)
        db.flush()
        return existing

    page = OcrPage(
        document_id=document_id,
        page_number=page_number,
        extracted_text=extracted_text,
        confidence_score=confidence_score,
        ocr_engine_version=ocr_engine_version,
        processing_timestamp=now,
    )
    db.add(page)
    db.flush()
    return page


def list_for_document(db: Session, document_id: str) -> list[OcrPage]:
    stmt = (
        select(OcrPage)
        .where(OcrPage.document_id == document_id)
        .order_by(OcrPage.page_number.asc())
    )
    return list(db.scalars(stmt).all())

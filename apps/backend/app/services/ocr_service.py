from sqlalchemy.orm import Session

from app.repositories import audit_repository, ocr_repository
from app.services.ocr_engine import PageOcrResult


def record_page(
    db: Session,
    *,
    document_id: str,
    page_number: int,
    result: PageOcrResult,
    engine_name: str,
    engine_version: str,
    actor: str,
) -> None:
    """Persist one page's OCR output and audit the write, in one transaction
    (ADR-011 storage + ADR-015 audit logging). Idempotent: safe to call again
    for the same (document_id, page_number) under Celery's at-least-once
    delivery (ADR-008)."""
    ocr_repository.upsert_page(
        db,
        document_id=document_id,
        page_number=page_number,
        extracted_text=result.text,
        confidence_score=result.confidence,
        ocr_engine_version=f"{engine_name}:{engine_version}",
    )
    audit_repository.record(
        db,
        entity_type="document",
        entity_id=document_id,
        action="ocr_page_recorded",
        actor=actor,
        details={
            "page_number": page_number,
            "confidence_score": result.confidence,
            "ocr_engine_version": f"{engine_name}:{engine_version}",
        },
    )
    db.commit()

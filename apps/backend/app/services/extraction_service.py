from typing import Any

from sqlalchemy.orm import Session

from app.repositories import audit_repository, extraction_repository


def record_extraction(
    db: Session,
    *,
    document_id: str,
    content: dict[str, Any],
    confidence_score: float,
    prompt_id: str,
    prompt_version: str,
    model_provider: str,
    model_name: str,
    actor: str,
) -> None:
    """Persist an extraction result and audit the write, in one transaction
    (ADR-013 versioning + ADR-015 audit logging). Idempotent per document_id."""
    extraction_repository.upsert(
        db,
        document_id=document_id,
        content=content,
        confidence_score=confidence_score,
        prompt_id=prompt_id,
        prompt_version=prompt_version,
        model_provider=model_provider,
        model_name=model_name,
    )
    audit_repository.record(
        db,
        entity_type="document",
        entity_id=document_id,
        action="extraction_recorded",
        actor=actor,
        details={
            "confidence_score": confidence_score,
            "prompt_id": prompt_id,
            "prompt_version": prompt_version,
            "model_provider": model_provider,
            "model_name": model_name,
        },
    )
    db.commit()

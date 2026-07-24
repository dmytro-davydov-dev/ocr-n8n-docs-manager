from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_internal_api_key
from app.repositories import document_repository
from app.schemas.document import DocumentStatusUpdate, DocumentSummary

router = APIRouter(
    prefix="/internal", tags=["internal"], dependencies=[Depends(require_internal_api_key)]
)


@router.get("/ping")
def internal_ping() -> dict[str, str]:
    return {"status": "ok", "scope": "internal"}


@router.patch("/documents/{document_id}/status", response_model=DocumentSummary)
def update_document_status(
    document_id: str, body: DocumentStatusUpdate, db: Session = Depends(get_db)
) -> DocumentSummary:
    """WS-04 (n8n) calls this to report processing progress/outcome for a
    document it is sequencing. n8n never writes to application tables
    directly (ADR-006, ADR-009) — this endpoint is the only path."""
    document = document_repository.get(db, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    try:
        document = document_repository.update_status(
            db,
            document,
            new_status=body.status,
            actor="n8n:workflow",
            error_message=body.error_message,
        )
    except document_repository.InvalidStatusTransition as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return DocumentSummary.model_validate(document)

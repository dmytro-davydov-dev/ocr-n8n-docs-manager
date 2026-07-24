from celery import chain
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_internal_api_key
from app.repositories import document_repository
from app.schemas.document import DocumentStatusUpdate, DocumentSummary
from app.tasks.embeddings import generate_embeddings
from app.tasks.extraction import extract_fields
from app.tasks.file_validation import validate_file
from app.tasks.ocr import run_ocr

router = APIRouter(
    prefix="/internal", tags=["internal"], dependencies=[Depends(require_internal_api_key)]
)


@router.get("/ping")
def internal_ping() -> dict[str, str]:
    return {"status": "ok", "scope": "internal"}


@router.post("/documents/{document_id}/process", status_code=status.HTTP_202_ACCEPTED)
def trigger_document_processing(document_id: str, db: Session = Depends(get_db)) -> dict[str, str]:
    """WS-04 (n8n) calls this once per upload to sequence the processing
    pipeline (validate -> OCR -> extract -> embed). This is the only path
    n8n has into Celery -- it never touches the broker directly (ADR-009).

    Dispatching is idempotent even under retry/duplicate webhook delivery:
    every task in the chain re-reads the document's current status before
    acting and no-ops if it has already moved past the status that task
    expects (see each task's docstring in app/tasks/), so a duplicate
    `.process` call against a document that's already mid-pipeline or done
    just runs a chain of no-ops rather than reprocessing or duplicating
    records.
    """
    document = document_repository.get(db, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    pipeline = chain(
        validate_file.si(document_id),
        run_ocr.si(document_id),
        extract_fields.si(document_id),
        generate_embeddings.si(document_id),
    )
    result = pipeline.apply_async()
    return {"document_id": document_id, "task_id": result.id}


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

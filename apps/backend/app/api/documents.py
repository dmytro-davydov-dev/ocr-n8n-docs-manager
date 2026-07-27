from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.internal import _dispatch_pipeline, _minutes_since_update
from app.core.config import settings
from app.core.database import get_db
from app.repositories import (
    audit_repository,
    chunk_repository,
    document_repository,
    extraction_repository,
    ocr_repository,
)
from app.schemas.chunk import ChunkOut
from app.schemas.document import DocumentSummary
from app.schemas.extraction import ExtractionOut
from app.schemas.ocr import OcrPageOut
from app.services import document_service

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocumentSummary, status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile, db: Session = Depends(get_db)) -> DocumentSummary:
    """FR-101/102/103/104/105: validate, persist, store, and trigger processing."""
    content = await file.read()
    content_type = file.content_type or "application/octet-stream"

    try:
        document = document_service.ingest_document(
            db,
            filename=file.filename or "unnamed",
            content_type=content_type,
            content=content,
            actor="api:upload",
        )
    except (document_service.UnsupportedFileType, document_service.FileTooLarge) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return DocumentSummary.model_validate(document)


@router.get("", response_model=list[DocumentSummary])
def list_documents(
    include_archived: bool = Query(False, alias="includeArchived"),
    db: Session = Depends(get_db),
) -> list[DocumentSummary]:
    """FR-107/108: list documents and their current status. Archived
    documents are hidden by default (?includeArchived=true to show them)."""
    documents = document_repository.list_all(db, include_archived=include_archived)
    return [DocumentSummary.model_validate(doc) for doc in documents]


@router.get("/{document_id}", response_model=DocumentSummary)
def get_document(document_id: str, db: Session = Depends(get_db)) -> DocumentSummary:
    """FR-107: fetch the current status of a single document."""
    document = document_repository.get(db, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return DocumentSummary.model_validate(document)


@router.post("/{document_id}/archive", response_model=DocumentSummary)
def archive_document(document_id: str, db: Session = Depends(get_db)) -> DocumentSummary:
    """Soft-remove a document from the default documents list. Independent
    of processing status -- see document_repository.archive."""
    document = document_repository.get(db, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    try:
        document = document_repository.archive(db, document, actor="api:archive")
    except document_repository.DocumentAlreadyArchived as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return DocumentSummary.model_validate(document)


@router.post("/{document_id}/unarchive", response_model=DocumentSummary)
def unarchive_document(document_id: str, db: Session = Depends(get_db)) -> DocumentSummary:
    document = document_repository.get(db, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    try:
        document = document_repository.unarchive(db, document, actor="api:archive")
    except document_repository.DocumentNotArchived as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return DocumentSummary.model_validate(document)


@router.post("/{document_id}/reprocess", response_model=DocumentSummary, status_code=status.HTTP_202_ACCEPTED)
def reprocess_document(document_id: str, db: Session = Depends(get_db)) -> DocumentSummary:
    """Public counterpart to `app.api.internal.trigger_document_reprocessing`
    (n8n/operator-only, gated behind INTERNAL_API_KEY) -- lets the frontend's
    "Reprocess" action (DocumentList.tsx) reset a `complete`/`failed`
    document, or force-unstick one wedged in `queued`/`processing` past
    `DOCUMENT_STUCK_THRESHOLD_MINUTES`, without the browser needing to hold
    the internal API key. Same rules as the internal endpoint apply; see its
    docstring for the full contract."""
    document = document_repository.get(db, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    if document.archived_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Document {document_id} is archived; unarchive it before reprocessing",
        )

    if document.status in ("queued", "processing"):
        age_minutes = _minutes_since_update(document)
        if age_minutes < settings.document_stuck_threshold_minutes:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Document {document_id} is '{document.status}' and was updated "
                    f"{age_minutes:.1f} minutes ago, within the "
                    f"{settings.document_stuck_threshold_minutes}-minute grace period a pipeline "
                    "run is allowed -- wait, or confirm it's genuinely wedged, before forcing a reprocess"
                ),
            )
    elif document.status not in ("complete", "failed"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Document {document_id} is '{document.status}'; reprocess does not apply",
        )

    document = document_repository.reset_retry_count(db, document)
    document = document_repository.update_status(db, document, new_status="queued", actor="api:reprocess")
    _dispatch_pipeline(document_id)
    return DocumentSummary.model_validate(document)


@router.get("/{document_id}/file")
def get_document_file(document_id: str, db: Session = Depends(get_db)) -> Response:
    """Serve the original stored file for viewing (e.g. WS-01's PDF viewer)."""
    document = document_repository.get(db, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    content = document_service.get_document_file(document)
    return Response(content=content, media_type=document.content_type)


@router.get("/{document_id}/ocr", response_model=list[OcrPageOut])
def get_document_ocr_pages(document_id: str, db: Session = Depends(get_db)) -> list[OcrPageOut]:
    """FR-207: page-level OCR output produced by WS-03's OCR pipeline (ADR-011)."""
    document = document_repository.get(db, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    pages = ocr_repository.list_for_document(db, document_id)
    return [OcrPageOut.model_validate(page) for page in pages]


@router.get("/{document_id}/extraction", response_model=ExtractionOut)
def get_document_extraction(document_id: str, db: Session = Depends(get_db)) -> ExtractionOut:
    """FR-307: AI extraction results produced by WS-03's extraction pipeline (ADR-012/013)."""
    document = document_repository.get(db, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    extraction = extraction_repository.get_for_document(db, document_id)
    if extraction is None:
        # FR-304: a prior schema-validation failure is queryable via the
        # audit trail (ADR-015), so "not yet attempted" (404) can be told
        # apart from "attempted and failed validation" (422).
        failure = audit_repository.get_latest(
            db,
            entity_type="document",
            entity_id=document_id,
            action="extraction_validation_failed",
        )
        if failure is not None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Extraction failed schema validation: {failure.details.get('reason', 'unknown error')}",
            )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Extraction not found")

    return ExtractionOut.model_validate(extraction)


@router.get("/{document_id}/chunks", response_model=list[ChunkOut])
def get_document_chunks(document_id: str, db: Session = Depends(get_db)) -> list[ChunkOut]:
    """RAG chunks + embedding metadata produced by WS-03's embedding pipeline (ADR-016/017/018)."""
    document = document_repository.get(db, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    chunks = chunk_repository.list_for_document(db, document_id)
    return [ChunkOut.model_validate(chunk) for chunk in chunks]

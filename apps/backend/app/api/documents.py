from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories import document_repository
from app.schemas.document import DocumentSummary
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
def list_documents(db: Session = Depends(get_db)) -> list[DocumentSummary]:
    """FR-107/108: list all documents and their current status."""
    documents = document_repository.list_all(db)
    return [DocumentSummary.model_validate(doc) for doc in documents]


@router.get("/{document_id}", response_model=DocumentSummary)
def get_document(document_id: str, db: Session = Depends(get_db)) -> DocumentSummary:
    """FR-107: fetch the current status of a single document."""
    document = document_repository.get(db, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return DocumentSummary.model_validate(document)


@router.get("/{document_id}/file")
def get_document_file(document_id: str, db: Session = Depends(get_db)) -> Response:
    """Serve the original stored file for viewing (e.g. WS-01's PDF viewer)."""
    document = document_repository.get(db, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    content = document_service.get_document_file(document)
    return Response(content=content, media_type=document.content_type)

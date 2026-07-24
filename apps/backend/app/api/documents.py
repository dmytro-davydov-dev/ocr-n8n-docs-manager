from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories import chunk_repository, document_repository, extraction_repository, ocr_repository
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

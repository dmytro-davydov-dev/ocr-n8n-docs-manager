from datetime import datetime, timezone

from celery import chain
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
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


def _dispatch_pipeline(document_id: str):
    pipeline = chain(
        validate_file.si(document_id),
        run_ocr.si(document_id),
        extract_fields.si(document_id),
        generate_embeddings.si(document_id),
    )
    return pipeline.apply_async()


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

    result = _dispatch_pipeline(document_id)
    return {"document_id": document_id, "task_id": result.id}


def _minutes_since_update(document) -> float:
    updated_at = document.updated_at
    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - updated_at).total_seconds() / 60


@router.post("/documents/{document_id}/reprocess", status_code=status.HTTP_202_ACCEPTED)
def trigger_document_reprocessing(document_id: str, db: Session = Depends(get_db)) -> dict[str, str]:
    """Reprocess a `complete` or `failed` document (e.g. after fixing an OCR
    engine issue, or to re-run with different OCR/LLM/embedding config).
    Previously there was no supported way to do this even though every task
    in the pipeline is idempotent and would have handled it correctly
    (ADR-011 anticipated reprocessing as a benefit of page-level OCR
    storage) -- see document_repository.ALLOWED_TRANSITIONS. Resets the
    document to `queued` (an explicit, audited transition) and re-dispatches
    the same chain used for first-time processing.

    Also doubles as the operator-driven unstick path for a document the
    watchdog has flagged as wedged in `queued`/`processing`
    (Progress.md Blockers #4 follow-up: "no automated recovery for
    stuck/failed documents" covered `failed` via auto-retry, but a document
    stuck mid-pipeline had no supported recovery at all -- see
    document_repository.ALLOWED_TRANSITIONS). That path is gated on the same
    `DOCUMENT_STUCK_THRESHOLD_MINUTES` staleness window the watchdog
    (`02-processing-watchdog.json`) uses to flag it in the first place, so a
    document that's genuinely still mid-pipeline can't be yanked out from
    under itself into a second, redundant chain."""
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

    # An explicit, operator-triggered reprocess is a fresh attempt, not one of
    # the watchdog's automatic ones -- give it a full auto-retry budget again
    # rather than letting it inherit whatever auto-retry had already used.
    document = document_repository.reset_retry_count(db, document)
    document = document_repository.update_status(db, document, new_status="queued", actor="api:reprocess")
    result = _dispatch_pipeline(document_id)
    return {"document_id": document_id, "task_id": result.id}


@router.post("/documents/{document_id}/auto-retry", status_code=status.HTTP_202_ACCEPTED)
def trigger_document_auto_retry(document_id: str, db: Session = Depends(get_db)) -> dict[str, str | int]:
    """Blocker: "no automated recovery for stuck/failed documents" -- the n8n
    watchdog (`02-processing-watchdog.json`) previously only surfaced
    `failed`/stuck documents for a human to `/reprocess` by hand. It now
    calls this endpoint instead, which applies a bounded auto-retry policy
    (`settings.document_auto_retry_max`) so unattended recovery is possible
    without silently retrying forever.

    Only `failed` documents are eligible -- a document stuck in
    `queued`/`processing` for >15 minutes (the watchdog's other alert
    condition) is a wedged worker/broker problem that re-dispatching the same
    chain wouldn't fix, and calling `/process` again on a document that's
    genuinely still mid-pipeline risks a second concurrent run; the watchdog
    still only surfaces those for a human, unchanged.
    """
    document = document_repository.get(db, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    if document.archived_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Document {document_id} is archived; unarchive it before retrying",
        )

    if document.status != "failed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Document {document_id} is '{document.status}'; auto-retry only applies to 'failed'",
        )

    if document.retry_count >= settings.document_auto_retry_max:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Document {document_id} has exhausted its auto-retry budget "
                f"({document.retry_count}/{settings.document_auto_retry_max}); "
                "needs a manual /reprocess or investigation"
            ),
        )

    document = document_repository.increment_retry_count(db, document)
    document = document_repository.update_status(db, document, new_status="queued", actor="api:auto-retry")
    result = _dispatch_pipeline(document_id)
    return {"document_id": document_id, "task_id": result.id, "retry_count": document.retry_count}


@router.post("/documents/{document_id}/reindex", status_code=status.HTTP_202_ACCEPTED)
def trigger_document_reindex(document_id: str, db: Session = Depends(get_db)) -> dict[str, str]:
    """FR-507: re-run chunking/embedding for a document on demand (e.g. after
    OCR was manually re-run, or a chunking/embedding config change). Safe to
    call any time -- `generate_embeddings` re-reads the document's current
    OCR text, upserts by (document_id, chunk_index), and drops any stale
    trailing chunks from a prior run (see chunk_repository.delete_from_index),
    so this never duplicates or leaves orphaned chunks behind."""
    document = document_repository.get(db, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    result = generate_embeddings.apply_async(args=[document_id])
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

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories import document_repository, review_repository
from app.schemas.review import (
    ReviewCreateRequest,
    ReviewRejectRequest,
    ReviewRevisionSummary,
    ReviewSaveDraftRequest,
    ReviewSummary,
    ReviewTransitionRequest,
)
from app.services import review_service

router = APIRouter(prefix="/documents/{document_id}/review", tags=["reviews"])


def _get_document_or_404(db: Session, document_id: str):
    document = document_repository.get(db, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


def _get_review_or_404(db: Session, document_id: str) -> review_repository.Review:
    review = review_repository.get_by_document(db, document_id)
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    return review


@router.post("", response_model=ReviewSummary, status_code=status.HTTP_201_CREATED)
def create_review(
    document_id: str, body: ReviewCreateRequest, db: Session = Depends(get_db)
) -> ReviewSummary:
    document = _get_document_or_404(db, document_id)
    try:
        review = review_service.start_review(db, document, actor="api:review", content=body.content)
    except review_service.DocumentNotReady as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except review_repository.ReviewAlreadyExists as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return ReviewSummary.model_validate(review)


@router.get("", response_model=ReviewSummary)
def get_review(document_id: str, db: Session = Depends(get_db)) -> ReviewSummary:
    _get_document_or_404(db, document_id)
    review = _get_review_or_404(db, document_id)
    return ReviewSummary.model_validate(review)


@router.patch("", response_model=ReviewSummary)
def save_draft(
    document_id: str, body: ReviewSaveDraftRequest, db: Session = Depends(get_db)
) -> ReviewSummary:
    """Save an edit to the current draft (ADR-014: preserves prior versions
    via ReviewRevision rather than overwriting history)."""
    _get_document_or_404(db, document_id)
    review = _get_review_or_404(db, document_id)
    try:
        review = review_repository.save_draft(
            db,
            review,
            content=body.content,
            expected_version=body.expected_version,
            actor="api:review",
        )
    except review_repository.InvalidReviewTransition as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except review_repository.ReviewVersionConflict as exc:
        raise HTTPException(status_code=status.HTTP_412_PRECONDITION_FAILED, detail=str(exc)) from exc
    return ReviewSummary.model_validate(review)


@router.post("/submit", response_model=ReviewSummary)
def submit_for_review(
    document_id: str, body: ReviewTransitionRequest, db: Session = Depends(get_db)
) -> ReviewSummary:
    return _transition(db, document_id, new_status="in_review", expected_version=body.expected_version)


@router.post("/approve", response_model=ReviewSummary)
def approve_review(
    document_id: str, body: ReviewTransitionRequest, db: Session = Depends(get_db)
) -> ReviewSummary:
    return _transition(db, document_id, new_status="approved", expected_version=body.expected_version)


@router.post("/reject", response_model=ReviewSummary)
def reject_review(
    document_id: str, body: ReviewRejectRequest, db: Session = Depends(get_db)
) -> ReviewSummary:
    return _transition(
        db,
        document_id,
        new_status="rejected",
        expected_version=body.expected_version,
        rejection_reason=body.reason,
    )


@router.post("/archive", response_model=ReviewSummary)
def archive_review(
    document_id: str, body: ReviewTransitionRequest, db: Session = Depends(get_db)
) -> ReviewSummary:
    return _transition(db, document_id, new_status="archived", expected_version=body.expected_version)


@router.get("/history", response_model=list[ReviewRevisionSummary])
def get_review_history(document_id: str, db: Session = Depends(get_db)) -> list[ReviewRevisionSummary]:
    """Phase-4 audit-history API: the append-only sequence of every review
    edit/transition, oldest first."""
    _get_document_or_404(db, document_id)
    review = _get_review_or_404(db, document_id)
    revisions = review_repository.list_revisions(db, review.id)
    return [ReviewRevisionSummary.model_validate(revision) for revision in revisions]


def _transition(
    db: Session,
    document_id: str,
    *,
    new_status: str,
    expected_version: int,
    rejection_reason: str | None = None,
) -> ReviewSummary:
    _get_document_or_404(db, document_id)
    review = _get_review_or_404(db, document_id)
    try:
        review = review_repository.transition(
            db,
            review,
            new_status=new_status,
            expected_version=expected_version,
            actor="api:review",
            rejection_reason=rejection_reason,
        )
    except review_repository.InvalidReviewTransition as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except review_repository.ReviewVersionConflict as exc:
        raise HTTPException(status_code=status.HTTP_412_PRECONDITION_FAILED, detail=str(exc)) from exc
    except review_repository.ReviewValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return ReviewSummary.model_validate(review)

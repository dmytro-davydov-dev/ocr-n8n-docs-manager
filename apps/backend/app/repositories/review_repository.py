from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.review import Review
from app.models.review_revision import ReviewRevision
from app.repositories import audit_repository

# ADR-014 review-lifecycle transitions. No boolean "approved" flag: status
# is the single source of truth and every change is explicit and validated.
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "draft_review": {"in_review", "archived"},
    "in_review": {"approved", "rejected", "draft_review"},
    "approved": {"archived"},
    "rejected": {"draft_review", "archived"},
    "archived": set(),
}


class InvalidReviewTransition(ValueError):
    pass


class ReviewVersionConflict(ValueError):
    """Raised when a caller's expected_version is stale (ADR-014: concurrent
    editing requires optimistic locking)."""


class ReviewValidationError(ValueError):
    pass


class ReviewAlreadyExists(ValueError):
    pass


def _write_revision(db: Session, review: Review, *, actor: str) -> None:
    db.add(
        ReviewRevision(
            review_id=review.id,
            version=review.version,
            status=review.status,
            content=review.content,
            actor=actor,
        )
    )


def create(db: Session, *, document_id: str, actor: str, content: dict[str, Any]) -> Review:
    existing = get_by_document(db, document_id)
    if existing is not None:
        raise ReviewAlreadyExists(f"Document {document_id} already has a review")

    review = Review(document_id=document_id, status="draft_review", version=1, content=content)
    db.add(review)
    db.flush()

    _write_revision(db, review, actor=actor)
    audit_repository.record(
        db,
        entity_type="review",
        entity_id=review.id,
        action="created",
        actor=actor,
        details={"document_id": document_id, "status": review.status, "version": review.version},
    )
    db.commit()
    db.refresh(review)
    return review


def get(db: Session, review_id: str) -> Review | None:
    return db.get(Review, review_id)


def get_by_document(db: Session, document_id: str) -> Review | None:
    stmt = select(Review).where(Review.document_id == document_id)
    return db.scalars(stmt).first()


def list_revisions(db: Session, review_id: str) -> list[ReviewRevision]:
    stmt = (
        select(ReviewRevision)
        .where(ReviewRevision.review_id == review_id)
        .order_by(ReviewRevision.version.asc())
    )
    return list(db.scalars(stmt).all())


def _check_version(review: Review, expected_version: int) -> None:
    if review.version != expected_version:
        raise ReviewVersionConflict(
            f"Review {review.id} is at version {review.version}, but caller expected {expected_version}. "
            "Reload and retry."
        )


def save_draft(
    db: Session, review: Review, *, content: dict[str, Any], expected_version: int, actor: str
) -> Review:
    """Editing is only permitted in `draft_review` (ADR-014: reviewers send
    a review back to draft before making further edits)."""
    if review.status != "draft_review":
        raise InvalidReviewTransition(
            f"Review {review.id} cannot be edited while in status '{review.status}'"
        )
    _check_version(review, expected_version)

    review.content = content
    review.version += 1
    db.add(review)
    db.flush()

    _write_revision(db, review, actor=actor)
    audit_repository.record(
        db,
        entity_type="review",
        entity_id=review.id,
        action="draft_saved",
        actor=actor,
        details={"version": review.version},
    )
    db.commit()
    db.refresh(review)
    return review


def transition(
    db: Session,
    review: Review,
    *,
    new_status: str,
    expected_version: int,
    actor: str,
    rejection_reason: str | None = None,
) -> Review:
    allowed = ALLOWED_TRANSITIONS.get(review.status, set())
    if new_status not in allowed:
        raise InvalidReviewTransition(
            f"Cannot transition review {review.id} from '{review.status}' to '{new_status}'"
        )
    _check_version(review, expected_version)

    if new_status == "approved" and not review.content:
        raise ReviewValidationError("Cannot approve a review with no content")
    if new_status == "rejected" and not rejection_reason:
        raise ReviewValidationError("A rejection reason is required")

    previous_status = review.status
    review.status = new_status
    review.rejection_reason = rejection_reason if new_status == "rejected" else None
    review.version += 1
    db.add(review)
    db.flush()

    _write_revision(db, review, actor=actor)
    audit_repository.record(
        db,
        entity_type="review",
        entity_id=review.id,
        action="status_changed",
        actor=actor,
        details={
            "from": previous_status,
            "to": new_status,
            "version": review.version,
            "rejection_reason": rejection_reason,
        },
    )
    db.commit()
    db.refresh(review)
    return review

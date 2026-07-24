import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

JSONVariant = JSON().with_variant(JSONB(), "postgresql")

# ADR-014's review-lifecycle slice of the full document state machine.
# "Uploaded" / "OCR Completed" / "AI Extracted" are document-level states
# (see Document.status / DOCUMENT_STATUSES); a Review exists only once a
# document reaches those and is itself created in `draft_review`.
REVIEW_STATUSES = ("draft_review", "in_review", "approved", "rejected", "archived")


class Review(Base):
    """One active review per document (ADR-014). Content edits never
    overwrite history in place — see ReviewRevision."""

    __tablename__ = "reviews"

    id: Mapped[str] = mapped_column(
        String(length=36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    document_id: Mapped[str] = mapped_column(
        String(length=36), ForeignKey("documents.id"), nullable=False, unique=True
    )
    status: Mapped[str] = mapped_column(String(length=32), nullable=False, default="draft_review")
    # Optimistic-lock counter (ADR-014 Risks: concurrent editing). Bumped on
    # every content or status change.
    version: Mapped[int] = mapped_column(Integer(), nullable=False, default=1)
    content: Mapped[dict[str, Any]] = mapped_column(JSONVariant, nullable=False, default=dict)
    rejection_reason: Mapped[str | None] = mapped_column(String(length=2048), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

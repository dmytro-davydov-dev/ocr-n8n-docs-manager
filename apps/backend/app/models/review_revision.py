import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

JSONVariant = JSON().with_variant(JSONB(), "postgresql")


class ReviewRevision(Base):
    """Append-only snapshot of a Review at each version (ADR-014: "user
    edits create a new review version while preserving the original AI
    output"). Never updated or deleted — this is the review's audit
    history, returned by the Phase-4 audit-history API."""

    __tablename__ = "review_revisions"

    id: Mapped[str] = mapped_column(
        String(length=36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    review_id: Mapped[str] = mapped_column(
        String(length=36), ForeignKey("reviews.id"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer(), nullable=False)
    status: Mapped[str] = mapped_column(String(length=32), nullable=False)
    content: Mapped[dict[str, Any]] = mapped_column(JSONVariant, nullable=False, default=dict)
    actor: Mapped[str] = mapped_column(String(length=128), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

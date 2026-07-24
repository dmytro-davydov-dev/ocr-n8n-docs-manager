import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

JSONVariant = JSON().with_variant(JSONB(), "postgresql")


class Extraction(Base):
    """AI extraction result (ADR-013: prompt id/version + model name recorded
    with every result). One row per document — re-running extraction
    overwrites it in place, matching Celery's idempotency requirements
    (ADR-008)."""

    __tablename__ = "extractions"

    id: Mapped[str] = mapped_column(
        String(length=36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    document_id: Mapped[str] = mapped_column(
        String(length=36), ForeignKey("documents.id"), nullable=False, unique=True
    )
    content: Mapped[dict[str, Any]] = mapped_column(JSONVariant, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float(), nullable=False)
    prompt_id: Mapped[str] = mapped_column(String(length=128), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(length=32), nullable=False)
    model_provider: Mapped[str] = mapped_column(String(length=64), nullable=False)
    model_name: Mapped[str] = mapped_column(String(length=128), nullable=False)

    processing_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

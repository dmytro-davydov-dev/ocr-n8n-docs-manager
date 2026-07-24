import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class OcrPage(Base):
    """Page-level OCR result (ADR-011). One row per (document_id, page_number);
    re-running OCR for a page overwrites it in place so results stay
    idempotent under Celery's at-least-once delivery (ADR-008)."""

    __tablename__ = "ocr_pages"
    __table_args__ = (UniqueConstraint("document_id", "page_number", name="uq_ocr_pages_document_page"),)

    id: Mapped[str] = mapped_column(
        String(length=36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    document_id: Mapped[str] = mapped_column(
        String(length=36), ForeignKey("documents.id"), nullable=False
    )
    page_number: Mapped[int] = mapped_column(Integer(), nullable=False)
    extracted_text: Mapped[str] = mapped_column(Text(), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float(), nullable=False)
    ocr_engine_version: Mapped[str] = mapped_column(String(length=128), nullable=False)

    processing_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

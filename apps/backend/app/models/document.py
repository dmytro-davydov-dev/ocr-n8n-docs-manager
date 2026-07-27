import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

DOCUMENT_STATUSES = ("uploaded", "queued", "processing", "complete", "failed")


class Document(Base):
    __tablename__ = "documents"

    # Stored as text (not the postgres-only UUID type) so the same schema
    # works against SQLite in unit tests without a dialect-specific column.
    id: Mapped[str] = mapped_column(
        String(length=36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    filename: Mapped[str] = mapped_column(String(length=255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(length=128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(length=64), nullable=False, index=True)
    storage_path: Mapped[str] = mapped_column(String(length=1024), nullable=False)
    status: Mapped[str] = mapped_column(String(length=32), nullable=False, default="uploaded", index=True)
    error_message: Mapped[str | None] = mapped_column(String(length=2048), nullable=True)
    # Blocker: "no automated recovery for stuck/failed documents" -- counts
    # auto-retries the watchdog (n8n `02-processing-watchdog`) has triggered
    # via POST /api/internal/documents/{id}/auto-retry, capped at
    # settings.document_auto_retry_max. Reset to 0 whenever an operator
    # explicitly reprocesses a document (POST .../reprocess), since that's a
    # deliberate new attempt, not another automatic one.
    retry_count: Mapped[int] = mapped_column(Integer(), nullable=False, default=0, server_default="0")
    # Soft-remove-from-list: set when a user archives a document from the
    # documents table. Deliberately a separate column rather than an
    # "archived" value on `status` -- `status` drives the processing state
    # machine (ALLOWED_TRANSITIONS) and pipeline dispatch; archiving is a
    # display/visibility concern that shouldn't require touching that
    # machine or coupling reprocess/auto-retry eligibility to it.
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

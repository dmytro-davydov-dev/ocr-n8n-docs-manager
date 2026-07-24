import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, func
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
    content_hash: Mapped[str] = mapped_column(String(length=64), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(length=1024), nullable=False)
    status: Mapped[str] = mapped_column(String(length=32), nullable=False, default="uploaded")
    error_message: Mapped[str | None] = mapped_column(String(length=2048), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

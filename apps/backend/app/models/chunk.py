import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

JSONVariant = JSON().with_variant(JSONB(), "postgresql")


class Chunk(Base):
    """RAG chunk with its embedding (ADR-016/017/018). One row per
    (document_id, chunk_index) — re-chunking/re-embedding overwrites in
    place (ADR-008 idempotency).

    The embedding vector is stored as a JSON float array rather than a
    native `pgvector` column for now: the shared Postgres image doesn't yet
    provision the `vector` extension (WS-05 infra work), and this keeps the
    model portable to the SQLite test database used across this suite. See
    Progress.md technical debt — swapping to a real `Vector` column is a
    follow-up migration, not a change to this pipeline's logic.
    """

    __tablename__ = "chunks"
    __table_args__ = (UniqueConstraint("document_id", "chunk_index", name="uq_chunks_document_index"),)

    id: Mapped[str] = mapped_column(
        String(length=36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    document_id: Mapped[str] = mapped_column(
        String(length=36), ForeignKey("documents.id"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer(), nullable=False)
    page_number: Mapped[int] = mapped_column(Integer(), nullable=False)
    start_offset: Mapped[int] = mapped_column(Integer(), nullable=False)
    end_offset: Mapped[int] = mapped_column(Integer(), nullable=False)
    text: Mapped[str] = mapped_column(Text(), nullable=False)
    token_count: Mapped[int] = mapped_column(Integer(), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(JSONVariant, nullable=False)
    embedding_provider: Mapped[str] = mapped_column(String(length=64), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(length=128), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

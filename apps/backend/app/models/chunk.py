import uuid
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import settings
from app.models.base import Base

JSONVariant = JSON().with_variant(JSONB(), "postgresql")

# ADR-016: a native pgvector column on Postgres (fixed-dimension, ANN-index-
# able), falling back to a plain JSON float array on SQLite -- the test
# suite runs against SQLite, which has no vector type, and pgvector's
# result/bind processors (`pgvector.sqlalchemy.Vector`) already read/write
# plain `list[float]` at the Python level (verified directly against the
# installed pgvector package: `Vector._from_db`/`_to_db` both operate on
# `list[float]`, never a numpy array), so this swap is transparent to every
# caller that already treats `chunk.embedding` as `list[float]`
# (`search_service`, `chunk_repository`, the AI pipeline tasks).
EmbeddingVariant = JSON().with_variant(Vector(settings.embedding_dimensions), "postgresql")


class Chunk(Base):
    """RAG chunk with its embedding (ADR-016/017/018). One row per
    (document_id, chunk_index) — re-chunking/re-embedding overwrites in
    place (ADR-008 idempotency)."""

    __tablename__ = "chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_chunks_document_index"),
        # ADR-016/019: HNSW ANN index, cosine ops to match search_service's
        # cosine-similarity ranking. Postgres-only (SQLite, used by this
        # test suite, has no vector type/HNSW access method) -- `ddl_if`
        # keeps `Base.metadata.create_all()` from attempting it against
        # SQLite; the real, versioned DDL lives in migration
        # 0008_chunks_hnsw, this declaration exists only so `alembic check`
        # doesn't see it as undeclared drift (the same class of bug fixed
        # for this table's other indexes -- see Progress.md).
        Index(
            "ix_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ).ddl_if(dialect="postgresql"),
    )

    id: Mapped[str] = mapped_column(
        String(length=36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    document_id: Mapped[str] = mapped_column(
        String(length=36), ForeignKey("documents.id"), nullable=False, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer(), nullable=False)
    page_number: Mapped[int] = mapped_column(Integer(), nullable=False)
    start_offset: Mapped[int] = mapped_column(Integer(), nullable=False)
    end_offset: Mapped[int] = mapped_column(Integer(), nullable=False)
    text: Mapped[str] = mapped_column(Text(), nullable=False)
    token_count: Mapped[int] = mapped_column(Integer(), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(EmbeddingVariant, nullable=False)
    embedding_provider: Mapped[str] = mapped_column(String(length=64), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(length=128), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

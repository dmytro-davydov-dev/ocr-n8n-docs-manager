"""chunks: HNSW ANN index on embedding (ADR-016/019)

Revision ID: 0008_chunks_hnsw
Revises: 0007_chunks_pgvector
Create Date: 2026-07-25 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0008_chunks_hnsw"
down_revision: str | None = "0007_chunks_pgvector"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Cosine distance matches search_service's cosine-similarity ranking
    # (ADR-019). HNSW over exact/IVFFlat: no training step, good recall at
    # this dataset size, and pgvector's recommended default for most
    # workloads.
    op.execute(
        "CREATE INDEX ix_chunks_embedding_hnsw ON chunks "
        "USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_chunks_embedding_hnsw")

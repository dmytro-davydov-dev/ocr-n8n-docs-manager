"""chunks: native pgvector column (ADR-016)

Revision ID: 0007_chunks_pgvector
Revises: 0006_chunks
Create Date: 2026-07-25 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0007_chunks_pgvector"
down_revision: str | None = "0006_chunks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Must match app.core.config.Settings.embedding_dimensions' default (1536,
# text-embedding-3-small). A future embedding model with a different output
# dimension needs its own migration -- pgvector enforces this at the
# database level.
EMBEDDING_DIMENSIONS = 1536


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    # pgvector's text form ("[0.1,0.2,...]") is syntactically a JSON array,
    # so the existing JSONB data casts straight through via its text
    # representation -- no per-row Python migration needed.
    op.alter_column(
        "chunks",
        "embedding",
        type_=Vector(EMBEDDING_DIMENSIONS),
        postgresql_using="(embedding::text)::vector",
    )


def downgrade() -> None:
    op.alter_column(
        "chunks",
        "embedding",
        type_=postgresql.JSONB(),
        postgresql_using="(embedding::text)::jsonb",
    )

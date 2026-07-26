"""documents: retry_count for automated recovery (Progress.md Blockers #4)

Revision ID: 0009_documents_retry_count
Revises: 0008_chunks_hnsw
Create Date: 2026-07-25 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0009_documents_retry_count"
down_revision: str | None = "0008_chunks_hnsw"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("documents", "retry_count")

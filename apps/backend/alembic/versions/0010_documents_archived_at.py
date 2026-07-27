"""documents: archived_at for soft-remove from the documents list

Revision ID: 0010_documents_archived_at
Revises: 0009_documents_retry_count
Create Date: 2026-07-26 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0010_documents_archived_at"
down_revision: str | None = "0009_documents_retry_count"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("documents", "archived_at")

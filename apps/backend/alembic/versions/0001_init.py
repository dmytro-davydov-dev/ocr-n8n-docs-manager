"""initial schema marker

Revision ID: 0001_init
Revises: 
Create Date: 2026-07-24 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0001_init"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="uploaded"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("documents")

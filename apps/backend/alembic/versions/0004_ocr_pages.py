"""ocr_pages (ADR-011)

Revision ID: 0004_ocr_pages
Revises: 0003_reviews
Create Date: 2026-07-24 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0004_ocr_pages"
down_revision: str | None = "0003_reviews"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ocr_pages",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("document_id", sa.String(length=36), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("ocr_engine_version", sa.String(length=128), nullable=False),
        sa.Column(
            "processing_timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("document_id", "page_number", name="uq_ocr_pages_document_page"),
    )
    op.create_index("ix_ocr_pages_document_id", "ocr_pages", ["document_id"])


def downgrade() -> None:
    op.drop_index("ix_ocr_pages_document_id", table_name="ocr_pages")
    op.drop_table("ocr_pages")

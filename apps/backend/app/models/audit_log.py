import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

# JSONB on PostgreSQL, portable JSON elsewhere (e.g. SQLite in unit tests).
JSONVariant = JSON().with_variant(JSONB(), "postgresql")


class AuditLog(Base):
    """Append-only record of every mutation, per ADR-015. Never updated or deleted."""

    __tablename__ = "audit_log"
    __table_args__ = (Index("ix_audit_log_entity", "entity_type", "entity_id"),)

    # Text UUID (not the postgres-only UUID type) so the schema also works
    # against SQLite in unit tests.
    id: Mapped[str] = mapped_column(
        String(length=36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    entity_type: Mapped[str] = mapped_column(String(length=64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(length=64), nullable=False)
    action: Mapped[str] = mapped_column(String(length=64), nullable=False)
    actor: Mapped[str] = mapped_column(String(length=128), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSONVariant, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

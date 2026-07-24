from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def get_latest(
    db: Session, *, entity_type: str, entity_id: str, action: str
) -> AuditLog | None:
    """Most recent audit entry matching entity + action, if any."""
    return db.scalar(
        select(AuditLog)
        .where(
            AuditLog.entity_type == entity_type,
            AuditLog.entity_id == entity_id,
            AuditLog.action == action,
        )
        .order_by(AuditLog.created_at.desc())
        .limit(1)
    )


def record(
    db: Session,
    *,
    entity_type: str,
    entity_id: str,
    action: str,
    actor: str,
    details: dict[str, Any] | None = None,
) -> AuditLog:
    """Append an audit-log entry in the caller's current transaction.

    Append-only per ADR-015: callers must never update or delete rows in
    this table, only insert.
    """
    entry = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        actor=actor,
        details=details or {},
    )
    db.add(entry)
    return entry

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.audit_event import AuditEvent


def record_audit_event(
    db: Session,
    *,
    actor_user_id: UUID | None,
    action: str,
    entity_type: str,
    entity_id: UUID | None = None,
    result: str = "success",
    details: dict[str, object] | None = None,
    commit: bool = True,
) -> AuditEvent:
    """Persist an audit event for an important platform action."""

    event = AuditEvent(
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        result=result,
        details=details,
    )

    db.add(event)

    if commit:
        db.commit()
        db.refresh(event)
    else:
        db.flush()

    return event
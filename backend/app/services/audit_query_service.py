from datetime import datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.audit_event import AuditEvent


def list_audit_events(
    db: Session,
    *,
    search: str | None = None,
    actor_user_id: UUID | None = None,
    action: str | None = None,
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    result: str | None = None,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[AuditEvent], int]:
    """Return audit events matching the supplied filters."""

    query = select(AuditEvent)
    count_query = select(func.count()).select_from(AuditEvent)

    filters = []

    if search:
        normalized_search = search.strip()

        if normalized_search:
            search_pattern = f"%{normalized_search}%"

            filters.append(
                or_(
                    AuditEvent.action.ilike(search_pattern),
                    AuditEvent.entity_type.ilike(search_pattern),
                    AuditEvent.result.ilike(search_pattern),
                )
            )

    if actor_user_id is not None:
        filters.append(
            AuditEvent.actor_user_id == actor_user_id
        )

    if action:
        filters.append(
            AuditEvent.action == action.strip().lower()
        )

    if entity_type:
        filters.append(
            AuditEvent.entity_type == entity_type.strip().lower()
        )

    if entity_id is not None:
        filters.append(
            AuditEvent.entity_id == entity_id
        )

    if result:
        filters.append(
            AuditEvent.result == result.strip().lower()
        )

    if start_at is not None:
        filters.append(
            AuditEvent.created_at >= start_at
        )

    if end_at is not None:
        filters.append(
            AuditEvent.created_at <= end_at
        )

    if filters:
        query = query.where(*filters)
        count_query = count_query.where(*filters)

    query = (
        query
        .order_by(
            AuditEvent.created_at.desc(),
            AuditEvent.id.desc(),
        )
        .offset(offset)
        .limit(limit)
    )

    events = list(db.scalars(query).all())
    total = db.scalar(count_query) or 0

    return events, total


def get_audit_event(
    db: Session,
    *,
    event_id: UUID,
) -> AuditEvent | None:
    """Return one audit event by ID."""

    return db.get(AuditEvent, event_id)
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.db.session import get_db
from app.models.audit_event import AuditEvent
from app.models.user import User
from app.schemas.audit import AuditEventListResponse, AuditEventResponse
from app.services.audit_query_service import (
    get_audit_event,
    list_audit_events,
)

router = APIRouter(
    prefix="/audit",
    tags=["Audit & Activity History"],
)


@router.get(
    "",
    response_model=AuditEventListResponse,
)
def list_audit_history(
    search: str | None = Query(default=None, max_length=150),
    actor_user_id: UUID | None = Query(default=None),
    action: str | None = Query(default=None, max_length=80),
    entity_type: str | None = Query(default=None, max_length=80),
    entity_id: UUID | None = Query(default=None),
    result: str | None = Query(default=None, max_length=30),
    start_at: datetime | None = Query(default=None),
    end_at: datetime | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("audit.read")),
) -> AuditEventListResponse:
    if start_at is not None and end_at is not None and start_at > end_at:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="start_at must be earlier than or equal to end_at.",
        )

    events, total = list_audit_events(
        db=db,
        search=search,
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        result=result,
        start_at=start_at,
        end_at=end_at,
        offset=offset,
        limit=limit,
    )

    return AuditEventListResponse(
        items=events,
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/{event_id}",
    response_model=AuditEventResponse,
)
def get_audit_history_event(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("audit.read")),
) -> AuditEvent:
    event = get_audit_event(
        db=db,
        event_id=event_id,
    )

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit event not found.",
        )

    return event
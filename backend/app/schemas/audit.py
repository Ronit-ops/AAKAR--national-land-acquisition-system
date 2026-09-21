from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    actor_user_id: UUID | None
    action: str
    entity_type: str
    entity_id: UUID | None
    result: str
    details: dict[str, object] | None
    created_at: datetime


class AuditEventListResponse(BaseModel):
    items: list[AuditEventResponse]
    total: int
    offset: int
    limit: int


class AuditEventFilters(BaseModel):
    search: str | None = Field(
        default=None,
        max_length=150,
    )
    actor_user_id: UUID | None = None
    action: str | None = Field(
        default=None,
        max_length=80,
    )
    entity_type: str | None = Field(
        default=None,
        max_length=80,
    )
    entity_id: UUID | None = None
    result: str | None = Field(
        default=None,
        max_length=30,
    )
    start_at: datetime | None = None
    end_at: datetime | None = None
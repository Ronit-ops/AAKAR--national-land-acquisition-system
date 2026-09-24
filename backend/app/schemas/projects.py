from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProjectResponse(BaseModel):
    """Public project representation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    sector: str
    description: str | None
    responsible_authority_id: UUID
    boundary: dict[str, Any] | None
    status: str
    created_by_user_id: UUID
    updated_by_user_id: UUID
    created_at: datetime
    updated_at: datetime


class ProjectListResponse(BaseModel):
    """Paginated project response."""

    items: list[ProjectResponse]
    total: int
    offset: int
    limit: int


class CreateProjectRequest(BaseModel):
    """Request body for creating a project."""

    code: str = Field(
        min_length=1,
        max_length=50,
    )
    name: str = Field(
        min_length=2,
        max_length=200,
    )
    sector: str = Field(
        min_length=1,
        max_length=100,
    )
    description: str | None = Field(
        default=None,
        max_length=5000,
    )
    responsible_authority_id: UUID
    boundary: dict[str, Any] | None = None


class UpdateProjectRequest(BaseModel):
    """Request body for updating a project."""

    code: str = Field(
        min_length=1,
        max_length=50,
    )
    name: str = Field(
        min_length=2,
        max_length=200,
    )
    sector: str = Field(
        min_length=1,
        max_length=100,
    )
    description: str | None = Field(
        default=None,
        max_length=5000,
    )
    responsible_authority_id: UUID
    boundary: dict[str, Any] | None = None


class ProjectStatusResponse(BaseModel):
    """Project lifecycle status response."""

    id: UUID
    status: str
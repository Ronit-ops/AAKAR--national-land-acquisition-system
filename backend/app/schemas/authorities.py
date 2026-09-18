from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AuthorityResponse(BaseModel):
    """Public authority representation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    department_id: UUID
    code: str
    name: str
    authority_type: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AuthorityListResponse(BaseModel):
    """Paginated authority response."""

    items: list[AuthorityResponse]
    total: int
    offset: int
    limit: int


class CreateAuthorityRequest(BaseModel):
    """Request body for creating an authority."""

    department_id: UUID
    code: str = Field(
        min_length=1,
        max_length=50,
    )
    name: str = Field(
        min_length=2,
        max_length=150,
    )
    authority_type: str = Field(
        min_length=1,
        max_length=20,
    )
    description: str | None = Field(
        default=None,
        max_length=5000,
    )


class UpdateAuthorityRequest(BaseModel):
    """Request body for updating an authority."""

    department_id: UUID
    code: str = Field(
        min_length=1,
        max_length=50,
    )
    name: str = Field(
        min_length=2,
        max_length=150,
    )
    authority_type: str = Field(
        min_length=1,
        max_length=20,
    )
    description: str | None = Field(
        default=None,
        max_length=5000,
    )


class UpdateAuthorityStatusRequest(BaseModel):
    """Request body for changing authority status."""

    is_active: bool

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DepartmentResponse(BaseModel):
    """Public department representation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class DepartmentListResponse(BaseModel):
    """Paginated department response."""

    items: list[DepartmentResponse]
    total: int
    offset: int
    limit: int


class CreateDepartmentRequest(BaseModel):
    """Request body for creating a department."""

    code: str = Field(
        min_length=1,
        max_length=50,
    )
    name: str = Field(
        min_length=2,
        max_length=150,
    )
    description: str | None = Field(
        default=None,
        max_length=5000,
    )


class UpdateDepartmentRequest(BaseModel):
    """Request body for updating a department."""

    code: str = Field(
        min_length=1,
        max_length=50,
    )
    name: str = Field(
        min_length=2,
        max_length=150,
    )
    description: str | None = Field(
        default=None,
        max_length=5000,
    )


class UpdateDepartmentStatusRequest(BaseModel):
    """Request body for changing department status."""

    is_active: bool

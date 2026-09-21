from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    resource: str
    action: str
    description: str | None
    is_system_permission: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PermissionListResponse(BaseModel):
    items: list[PermissionResponse]
    total: int
    offset: int
    limit: int


class CreatePermissionRequest(BaseModel):
    code: str = Field(
        min_length=1,
        max_length=100,
        description="Machine-readable AAKAR permission code.",
    )
    name: str = Field(
        min_length=1,
        max_length=150,
    )
    resource: str = Field(
        min_length=1,
        max_length=80,
    )
    action: str = Field(
        min_length=1,
        max_length=80,
    )
    description: str | None = Field(
        default=None,
    )


class UpdatePermissionRequest(BaseModel):
    code: str = Field(
        min_length=1,
        max_length=100,
        description="Machine-readable AAKAR permission code.",
    )
    name: str = Field(
        min_length=1,
        max_length=150,
    )
    resource: str = Field(
        min_length=1,
        max_length=80,
    )
    action: str = Field(
        min_length=1,
        max_length=80,
    )
    description: str | None = Field(
        default=None,
    )


class UpdatePermissionStatusRequest(BaseModel):
    is_active: bool


class RolePermissionAssignmentRequest(BaseModel):
    permission_code: str = Field(
        min_length=1,
        max_length=100,
        description="Machine-readable AAKAR permission code.",
    )


class RolePermissionAssignmentResponse(BaseModel):
    role_id: UUID
    permission_id: UUID
    role_code: str
    permission_code: str
    assigned_at: datetime
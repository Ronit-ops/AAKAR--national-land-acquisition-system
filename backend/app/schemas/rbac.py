from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    scope_level: str
    description: str | None
    is_system_role: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserRolesResponse(BaseModel):
    user_id: UUID
    roles: list[RoleResponse]


class RoleAssignmentRequest(BaseModel):
    role_code: str = Field(
        min_length=1,
        max_length=80,
        description="Machine-readable AAKAR role code.",
    )


class RoleAssignmentResponse(BaseModel):
    user_id: UUID
    role: RoleResponse
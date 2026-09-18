from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.rbac import RoleResponse


class ManagedUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    full_name: str
    is_active: bool
    is_email_verified: bool
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ManagedUserDetailResponse(ManagedUserResponse):
    roles: list[RoleResponse]


class UserListResponse(BaseModel):
    items: list[ManagedUserResponse]
    total: int
    offset: int
    limit: int


class CreateManagedUserRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=150)


class UpdateManagedUserRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=150)


class UpdateUserStatusRequest(BaseModel):
    is_active: bool


class UpdateUserOrganizationRequest(BaseModel):
    department_id: UUID | None = None
    authority_id: UUID | None = None
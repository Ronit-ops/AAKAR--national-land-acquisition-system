from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_user,
    require_role,
)
from app.db.session import get_db
from app.models.role import Role
from app.models.user import User
from app.schemas.rbac import (
    RoleAssignmentRequest,
    RoleAssignmentResponse,
    RoleResponse,
    UserRolesResponse,
)
from app.services.rbac_service import (
    assign_role,
    get_user_roles,
    remove_role,
)


router = APIRouter(
    prefix="/rbac",
    tags=["RBAC"],
)


CurrentUser = Annotated[User, Depends(get_current_user)]
SystemAdministrator = Annotated[
    User,
    Depends(require_role("system_administrator")),
]


@router.get(
    "/me",
    response_model=UserRolesResponse,
)
def get_my_roles(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    roles = get_user_roles(
        db=db,
        user_id=current_user.id,
    )

    return UserRolesResponse(
        user_id=current_user.id,
        roles=roles,
    )


@router.get(
    "/roles",
    response_model=list[RoleResponse],
)
def list_active_roles(
    current_user: CurrentUser,
    db: Session = Depends(get_db),
):
    del current_user

    statement = (
        select(Role)
        .where(Role.is_active.is_(True))
        .order_by(Role.scope_level, Role.code)
    )

    return list(db.scalars(statement).all())


@router.post(
    "/users/{user_id}/roles",
    response_model=RoleAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def assign_user_role(
    user_id: UUID,
    payload: RoleAssignmentRequest,
    current_user: SystemAdministrator,
    db: Session = Depends(get_db),
):
    del current_user

    user = db.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    role = db.scalar(
        select(Role).where(
            Role.code == payload.role_code.strip().lower(),
        )
    )

    if role is None or not role.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active role not found.",
        )

    assignment = assign_role(
        db=db,
        user_id=user_id,
        role_code=role.code,
    )

    return RoleAssignmentResponse(
        user_id=assignment.user_id,
        role=role,
    )


@router.delete(
    "/users/{user_id}/roles/{role_code}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_user_role(
    user_id: UUID,
    role_code: str,
    current_user: SystemAdministrator,
    db: Session = Depends(get_db),
):
    del current_user

    user = db.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    removed = remove_role(
        db=db,
        user_id=user_id,
        role_code=role_code,
    )

    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role assignment not found.",
        )
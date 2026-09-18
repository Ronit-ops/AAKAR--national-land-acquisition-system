from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.users import (
    CreateManagedUserRequest,
    ManagedUserDetailResponse,
    ManagedUserResponse,
    UpdateManagedUserRequest,
    UpdateUserStatusRequest,
    UserListResponse,
)
from app.services.audit_service import record_audit_event
from app.services.auth_service import create_user
from app.services.rbac_service import get_user_roles
from app.services.user_management_service import (
    get_user,
    list_users,
    set_user_active_status,
    update_user_profile,
)


router = APIRouter(
    prefix="/users",
    tags=["User Management"],
)


SystemAdministrator = Annotated[
    User,
    Depends(require_role("system_administrator")),
]


@router.get(
    "",
    response_model=UserListResponse,
)
def list_managed_users(
    current_user: SystemAdministrator,
    db: Session = Depends(get_db),
    search: str | None = Query(
        default=None,
        max_length=150,
    ),
    is_active: bool | None = Query(default=None),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
    ),
) -> UserListResponse:
    del current_user

    users, total = list_users(
        db=db,
        search=search,
        is_active=is_active,
        offset=offset,
        limit=limit,
    )

    return UserListResponse(
        items=users,
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/{user_id}",
    response_model=ManagedUserDetailResponse,
)
def get_managed_user(
    user_id: UUID,
    current_user: SystemAdministrator,
    db: Session = Depends(get_db),
) -> ManagedUserDetailResponse:
    del current_user

    user = get_user(
        db=db,
        user_id=user_id,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    roles = get_user_roles(
        db=db,
        user_id=user.id,
    )

    return ManagedUserDetailResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_email_verified=user.is_email_verified,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        updated_at=user.updated_at,
        roles=roles,
    )


@router.post(
    "",
    response_model=ManagedUserResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_managed_user(
    payload: CreateManagedUserRequest,
    current_user: SystemAdministrator,
    db: Session = Depends(get_db),
) -> ManagedUserResponse:
    try:
        user = create_user(
            db=db,
            email=payload.email,
            password=payload.password,
            full_name=payload.full_name,
            commit=False,
        )

        record_audit_event(
            db=db,
            actor_user_id=current_user.id,
            action="user_created",
            entity_type="user",
            entity_id=user.id,
            details={
                "email": user.email,
                "full_name": user.full_name,
            },
            commit=False,
        )

        db.commit()
        db.refresh(user)

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        ) from None

    except SQLAlchemyError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create the user account.",
        ) from None

    return ManagedUserResponse.model_validate(user)


@router.patch(
    "/{user_id}",
    response_model=ManagedUserResponse,
)
def update_managed_user(
    user_id: UUID,
    payload: UpdateManagedUserRequest,
    current_user: SystemAdministrator,
    db: Session = Depends(get_db),
) -> ManagedUserResponse:
    try:
        user = update_user_profile(
            db=db,
            user_id=user_id,
            full_name=payload.full_name,
            email=payload.email,
            commit=False,
        )
    except ValueError as error:
        message = str(error)

        if message == "User not found.":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=message,
            ) from None

        if message == "A user with this email already exists.":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=message,
            ) from None

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=message,
        ) from None

    try:
        record_audit_event(
            db=db,
            actor_user_id=current_user.id,
            action="user_profile_updated",
            entity_type="user",
            entity_id=user.id,
            details={
                "fields": [
                    "full_name",
                    "email",
                ],
            },
            commit=False,
        )

        db.commit()
        db.refresh(user)

    except SQLAlchemyError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to update the user profile.",
        ) from None

    return ManagedUserResponse.model_validate(user)


@router.patch(
    "/{user_id}/status",
    response_model=ManagedUserResponse,
)
def update_managed_user_status(
    user_id: UUID,
    payload: UpdateUserStatusRequest,
    current_user: SystemAdministrator,
    db: Session = Depends(get_db),
) -> ManagedUserResponse:
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A system administrator cannot change their own active status.",
        )

    try:
        user = set_user_active_status(
            db=db,
            user_id=user_id,
            is_active=payload.is_active,
            commit=False,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from None

    try:
        record_audit_event(
            db=db,
            actor_user_id=current_user.id,
            action="user_status_changed",
            entity_type="user",
            entity_id=user.id,
            details={
                "is_active": user.is_active,
            },
            commit=False,
        )

        db.commit()
        db.refresh(user)

    except SQLAlchemyError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to change the user account status.",
        ) from None

    return ManagedUserResponse.model_validate(user)
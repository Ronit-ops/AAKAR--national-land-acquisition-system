from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.user import User
from app.schemas.permissions import (
    CreatePermissionRequest,
    PermissionListResponse,
    PermissionResponse,
    RolePermissionAssignmentRequest,
    RolePermissionAssignmentResponse,
    UpdatePermissionRequest,
    UpdatePermissionStatusRequest,
)
from app.services.audit_service import record_audit_event
from app.services.permission_service import (
    create_permission,
    get_permission,
    list_permissions,
    set_permission_active_status,
    update_permission,
)
from app.services.rbac_service import (
    assign_permission_to_role,
    get_role_permissions,
    remove_permission_from_role,
)


router = APIRouter(
    prefix="/permissions",
    tags=["Permission Management"],
)


CurrentUser = Annotated[User, Depends(get_current_user)]

SystemAdministrator = Annotated[
    User,
    Depends(require_role("system_administrator")),
]


@router.get(
    "",
    response_model=PermissionListResponse,
)
def list_permission_records(
    current_user: SystemAdministrator,
    search: str | None = Query(
        default=None,
        max_length=150,
    ),
    resource: str | None = Query(
        default=None,
        max_length=80,
    ),
    action: str | None = Query(
        default=None,
        max_length=80,
    ),
    is_active: bool | None = None,
    offset: int = Query(
        default=0,
        ge=0,
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
    ),
    db: Session = Depends(get_db),
):
    del current_user

    permissions, total = list_permissions(
        db=db,
        search=search,
        resource=resource,
        action=action,
        is_active=is_active,
        offset=offset,
        limit=limit,
    )

    return PermissionListResponse(
        items=permissions,
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/{permission_id}",
    response_model=PermissionResponse,
)
def get_permission_record(
    permission_id: UUID,
    current_user: SystemAdministrator,
    db: Session = Depends(get_db),
):
    del current_user

    permission = get_permission(
        db=db,
        permission_id=permission_id,
    )

    if permission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found.",
        )

    return permission


@router.post(
    "",
    response_model=PermissionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_permission_record(
    payload: CreatePermissionRequest,
    current_user: SystemAdministrator,
    db: Session = Depends(get_db),
):
    try:
        permission = create_permission(
            db=db,
            code=payload.code,
            name=payload.name,
            resource=payload.resource,
            action=payload.action,
            description=payload.description,
            is_system_permission=True,
            commit=False,
        )

        record_audit_event(
            db=db,
            actor_user_id=current_user.id,
            action="permission_created",
            entity_type="permission",
            entity_id=permission.id,
            result="success",
            details={
                "permission_code": permission.code,
                "resource": permission.resource,
                "action": permission.action,
            },
            commit=False,
        )

        db.commit()
        db.refresh(permission)

        return permission

    except ValueError as exc:
        db.rollback()

        if str(exc) == "A permission with this code already exists.":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(exc),
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    except SQLAlchemyError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create permission.",
        ) from exc


@router.patch(
    "/{permission_id}",
    response_model=PermissionResponse,
)
def update_permission_record(
    permission_id: UUID,
    payload: UpdatePermissionRequest,
    current_user: SystemAdministrator,
    db: Session = Depends(get_db),
):
    try:
        permission = update_permission(
            db=db,
            permission_id=permission_id,
            code=payload.code,
            name=payload.name,
            resource=payload.resource,
            action=payload.action,
            description=payload.description,
            commit=False,
        )

        record_audit_event(
            db=db,
            actor_user_id=current_user.id,
            action="permission_updated",
            entity_type="permission",
            entity_id=permission.id,
            result="success",
            details={
                "permission_code": permission.code,
                "resource": permission.resource,
                "action": permission.action,
            },
            commit=False,
        )

        db.commit()
        db.refresh(permission)

        return permission

    except ValueError as exc:
        db.rollback()

        message = str(exc)

        if message == "Permission not found.":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=message,
            ) from exc

        if message == "A permission with this code already exists.":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=message,
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=message,
        ) from exc

    except SQLAlchemyError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to update permission.",
        ) from exc


@router.patch(
    "/{permission_id}/status",
    response_model=PermissionResponse,
)
def update_permission_status(
    permission_id: UUID,
    payload: UpdatePermissionStatusRequest,
    current_user: SystemAdministrator,
    db: Session = Depends(get_db),
):
    try:
        permission = set_permission_active_status(
            db=db,
            permission_id=permission_id,
            is_active=payload.is_active,
            commit=False,
        )

        record_audit_event(
            db=db,
            actor_user_id=current_user.id,
            action="permission_status_changed",
            entity_type="permission",
            entity_id=permission.id,
            result="success",
            details={
                "permission_code": permission.code,
                "is_active": permission.is_active,
            },
            commit=False,
        )

        db.commit()
        db.refresh(permission)

        return permission

    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except SQLAlchemyError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to update permission status.",
        ) from exc


@router.get(
    "/roles/{role_code}",
    response_model=list[RolePermissionAssignmentResponse],
)
def list_role_permissions(
    role_code: str,
    current_user: SystemAdministrator,
    db: Session = Depends(get_db),
):
    del current_user

    normalized_role_code = role_code.strip().lower()

    try:
        assignments = get_role_permissions(
            db=db,
            role_code=normalized_role_code,
        )

        role = db.scalar(
            select(Role).where(
                Role.code == normalized_role_code,
            )
        )

        if role is None or not role.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Active role not found.",
            )

        return [
            RolePermissionAssignmentResponse(
                role_id=assignment.role_id,
                permission_id=assignment.permission_id,
                role_code=role.code,
                permission_code=assignment.permission.code,
                assigned_at=assignment.assigned_at,
            )
            for assignment in assignments
        ]

    except HTTPException:
        raise

    except ValueError as exc:
        if str(exc) == "Active role not found.":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    except SQLAlchemyError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve role permissions.",
        ) from exc


@router.post(
    "/roles/{role_code}/assign",
    response_model=RolePermissionAssignmentResponse,
)
def assign_role_permission(
    role_code: str,
    payload: RolePermissionAssignmentRequest,
    current_user: SystemAdministrator,
    db: Session = Depends(get_db),
):
    normalized_role_code = role_code.strip().lower()
    normalized_permission_code = payload.permission_code.strip().lower()

    role = db.scalar(
        select(Role).where(
            Role.code == normalized_role_code,
        )
    )

    if role is None or not role.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active role not found.",
        )

    permission = db.scalar(
        select(Permission).where(
            Permission.code == normalized_permission_code,
        )
    )

    if permission is None or not permission.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active permission not found.",
        )

    existing_assignment = db.scalar(
        select(RolePermission).where(
            RolePermission.role_id == role.id,
            RolePermission.permission_id == permission.id,
        )
    )

    try:
        assignment = assign_permission_to_role(
            db=db,
            role_code=normalized_role_code,
            permission_code=normalized_permission_code,
        )

        if existing_assignment is None:
            record_audit_event(
                db=db,
                actor_user_id=current_user.id,
                action="role_permission_assigned",
                entity_type="role_permission",
                entity_id=permission.id,
                result="success",
                details={
                    "role_code": role.code,
                    "permission_code": permission.code,
                },
                commit=True,
            )

        return RolePermissionAssignmentResponse(
            role_id=assignment.role_id,
            permission_id=assignment.permission_id,
            role_code=role.code,
            permission_code=permission.code,
            assigned_at=assignment.assigned_at,
        )

    except ValueError as exc:
        db.rollback()

        message = str(exc)

        if message in {
            "Active role not found.",
            "Active permission not found.",
        }:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=message,
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=message,
        ) from exc

    except SQLAlchemyError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to assign permission to role.",
        ) from exc


@router.delete(
    "/roles/{role_code}/assign/{permission_code}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_role_permission(
    role_code: str,
    permission_code: str,
    current_user: SystemAdministrator,
    db: Session = Depends(get_db),
):
    normalized_role_code = role_code.strip().lower()
    normalized_permission_code = permission_code.strip().lower()

    role = db.scalar(
        select(Role).where(
            Role.code == normalized_role_code,
        )
    )

    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found.",
        )

    permission = db.scalar(
        select(Permission).where(
            Permission.code == normalized_permission_code,
        )
    )

    if permission is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found.",
        )

    try:
        removed = remove_permission_from_role(
            db=db,
            role_code=normalized_role_code,
            permission_code=normalized_permission_code,
        )

        if not removed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role permission assignment not found.",
            )

        record_audit_event(
            db=db,
            actor_user_id=current_user.id,
            action="role_permission_removed",
            entity_type="role_permission",
            entity_id=permission.id,
            result="success",
            details={
                "role_code": role.code,
                "permission_code": permission.code,
            },
            commit=True,
        )

    except HTTPException:
        raise

    except SQLAlchemyError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to remove permission from role.",
        ) from exc
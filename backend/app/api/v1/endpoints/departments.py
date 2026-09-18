from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.departments import (
    CreateDepartmentRequest,
    DepartmentListResponse,
    DepartmentResponse,
    UpdateDepartmentRequest,
    UpdateDepartmentStatusRequest,
)
from app.services.audit_service import record_audit_event
from app.services.department_service import (
    create_department,
    get_department,
    list_departments,
    set_department_active_status,
    update_department,
)


router = APIRouter(
    prefix="/departments",
    tags=["Department Management"],
)


SystemAdministrator = Annotated[
    User,
    Depends(require_role("system_administrator")),
]


@router.get(
    "",
    response_model=DepartmentListResponse,
)
def list_managed_departments(
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
) -> DepartmentListResponse:
    del current_user

    departments, total = list_departments(
        db=db,
        search=search,
        is_active=is_active,
        offset=offset,
        limit=limit,
    )

    return DepartmentListResponse(
        items=departments,
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/{department_id}",
    response_model=DepartmentResponse,
)
def get_managed_department(
    department_id: UUID,
    current_user: SystemAdministrator,
    db: Session = Depends(get_db),
) -> DepartmentResponse:
    del current_user

    department = get_department(
        db=db,
        department_id=department_id,
    )

    if department is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found.",
        )

    return DepartmentResponse.model_validate(department)


@router.post(
    "",
    response_model=DepartmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_managed_department(
    payload: CreateDepartmentRequest,
    current_user: SystemAdministrator,
    db: Session = Depends(get_db),
) -> DepartmentResponse:
    try:
        department = create_department(
            db=db,
            code=payload.code,
            name=payload.name,
            description=payload.description,
            commit=False,
        )

        record_audit_event(
            db=db,
            actor_user_id=current_user.id,
            action="department_created",
            entity_type="department",
            entity_id=department.id,
            details={
                "code": department.code,
                "name": department.name,
            },
            commit=False,
        )

        db.commit()
        db.refresh(department)

    except ValueError as error:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from None

    except SQLAlchemyError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create the department.",
        ) from None

    return DepartmentResponse.model_validate(department)


@router.patch(
    "/{department_id}",
    response_model=DepartmentResponse,
)
def update_managed_department(
    department_id: UUID,
    payload: UpdateDepartmentRequest,
    current_user: SystemAdministrator,
    db: Session = Depends(get_db),
) -> DepartmentResponse:
    try:
        department = update_department(
            db=db,
            department_id=department_id,
            code=payload.code,
            name=payload.name,
            description=payload.description,
            commit=False,
        )
    except ValueError as error:
        message = str(error)

        if message == "Department not found.":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=message,
            ) from None

        if message == "A department with this code already exists.":
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
            action="department_updated",
            entity_type="department",
            entity_id=department.id,
            details={
                "fields": [
                    "code",
                    "name",
                    "description",
                ],
            },
            commit=False,
        )

        db.commit()
        db.refresh(department)

    except SQLAlchemyError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to update the department.",
        ) from None

    return DepartmentResponse.model_validate(department)


@router.patch(
    "/{department_id}/status",
    response_model=DepartmentResponse,
)
def update_managed_department_status(
    department_id: UUID,
    payload: UpdateDepartmentStatusRequest,
    current_user: SystemAdministrator,
    db: Session = Depends(get_db),
) -> DepartmentResponse:
    try:
        department = set_department_active_status(
            db=db,
            department_id=department_id,
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
            action="department_status_changed",
            entity_type="department",
            entity_id=department.id,
            details={
                "is_active": department.is_active,
            },
            commit=False,
        )

        db.commit()
        db.refresh(department)

    except SQLAlchemyError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to change the department status.",
        ) from None

    return DepartmentResponse.model_validate(department)

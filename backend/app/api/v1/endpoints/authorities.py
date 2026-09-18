from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.authorities import (
    AuthorityListResponse,
    AuthorityResponse,
    CreateAuthorityRequest,
    UpdateAuthorityRequest,
    UpdateAuthorityStatusRequest,
)
from app.services.audit_service import record_audit_event
from app.services.authority_service import (
    create_authority,
    get_authority,
    list_authorities,
    set_authority_active_status,
    update_authority,
)


router = APIRouter(
    prefix="/authorities",
    tags=["Authority Management"],
)


SystemAdministrator = Annotated[
    User,
    Depends(require_role("system_administrator")),
]


@router.get(
    "",
    response_model=AuthorityListResponse,
)
def list_managed_authorities(
    current_user: SystemAdministrator,
    db: Session = Depends(get_db),
    search: str | None = Query(
        default=None,
        max_length=150,
    ),
    department_id: UUID | None = Query(default=None),
    authority_type: str | None = Query(
        default=None,
        max_length=20,
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
) -> AuthorityListResponse:
    del current_user

    try:
        authorities, total = list_authorities(
            db=db,
            search=search,
            department_id=department_id,
            authority_type=authority_type,
            is_active=is_active,
            offset=offset,
            limit=limit,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from None

    return AuthorityListResponse(
        items=authorities,
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/{authority_id}",
    response_model=AuthorityResponse,
)
def get_managed_authority(
    authority_id: UUID,
    current_user: SystemAdministrator,
    db: Session = Depends(get_db),
) -> AuthorityResponse:
    del current_user

    authority = get_authority(
        db=db,
        authority_id=authority_id,
    )

    if authority is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Authority not found.",
        )

    return AuthorityResponse.model_validate(authority)


@router.post(
    "",
    response_model=AuthorityResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_managed_authority(
    payload: CreateAuthorityRequest,
    current_user: SystemAdministrator,
    db: Session = Depends(get_db),
) -> AuthorityResponse:
    try:
        authority = create_authority(
            db=db,
            department_id=payload.department_id,
            code=payload.code,
            name=payload.name,
            authority_type=payload.authority_type,
            description=payload.description,
            commit=False,
        )

        record_audit_event(
            db=db,
            actor_user_id=current_user.id,
            action="authority_created",
            entity_type="authority",
            entity_id=authority.id,
            details={
                "department_id": str(authority.department_id),
                "code": authority.code,
                "name": authority.name,
                "authority_type": authority.authority_type,
            },
            commit=False,
        )

        db.commit()
        db.refresh(authority)

    except ValueError as error:
        db.rollback()

        message = str(error)

        if message == "Department not found.":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=message,
            ) from None

        if message == "Cannot create an authority under an inactive department.":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=message,
            ) from None

        if message == "An authority with this code already exists.":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=message,
            ) from None

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=message,
        ) from None

    except SQLAlchemyError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create the authority.",
        ) from None

    return AuthorityResponse.model_validate(authority)


@router.patch(
    "/{authority_id}",
    response_model=AuthorityResponse,
)
def update_managed_authority(
    authority_id: UUID,
    payload: UpdateAuthorityRequest,
    current_user: SystemAdministrator,
    db: Session = Depends(get_db),
) -> AuthorityResponse:
    try:
        authority = update_authority(
            db=db,
            authority_id=authority_id,
            department_id=payload.department_id,
            code=payload.code,
            name=payload.name,
            authority_type=payload.authority_type,
            description=payload.description,
            commit=False,
        )
    except ValueError as error:
        message = str(error)

        if message in {
            "Authority not found.",
            "Department not found.",
        }:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=message,
            ) from None

        if message in {
            "Cannot assign an authority to an inactive department.",
            "An authority with this code already exists.",
        }:
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
            action="authority_updated",
            entity_type="authority",
            entity_id=authority.id,
            details={
                "fields": [
                    "department_id",
                    "code",
                    "name",
                    "authority_type",
                    "description",
                ],
            },
            commit=False,
        )

        db.commit()
        db.refresh(authority)

    except SQLAlchemyError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to update the authority.",
        ) from None

    return AuthorityResponse.model_validate(authority)


@router.patch(
    "/{authority_id}/status",
    response_model=AuthorityResponse,
)
def update_managed_authority_status(
    authority_id: UUID,
    payload: UpdateAuthorityStatusRequest,
    current_user: SystemAdministrator,
    db: Session = Depends(get_db),
) -> AuthorityResponse:
    try:
        authority = set_authority_active_status(
            db=db,
            authority_id=authority_id,
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
            action="authority_status_changed",
            entity_type="authority",
            entity_id=authority.id,
            details={
                "is_active": authority.is_active,
            },
            commit=False,
        )

        db.commit()
        db.refresh(authority)

    except SQLAlchemyError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to change the authority status.",
        ) from None

    return AuthorityResponse.model_validate(authority)

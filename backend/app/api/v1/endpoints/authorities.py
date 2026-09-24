from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_permission, require_role
from app.models.user import User
from app.schemas.authorities import (
    AuthorityListResponse,
    AuthorityResponse,
    CreateAuthorityRequest,
    UpdateAuthorityRequest,
    UpdateAuthorityStatusRequest,
)
from app.services.authority_service import (
    create_authority,
    get_authority,
    list_authorities,
    set_authority_active_status,
    update_authority,
)


router = APIRouter(
    prefix="/authorities",
    tags=["Authorities"],
)


SystemAdministrator = Annotated[
    User,
    Depends(require_role("system_administrator")),
]


AuthorityReader = Annotated[
    User,
    Depends(require_permission("authority.read")),
]


@router.get(
    "",
    response_model=AuthorityListResponse,
    status_code=status.HTTP_200_OK,
)
def list_managed_authorities(
    db: Session = Depends(get_db),
    current_user: AuthorityReader = None,
    search: str | None = Query(
        default=None,
        description="Search authorities by code or name.",
    ),
    department_id: UUID | None = Query(
        default=None,
        description="Filter authorities by department.",
    ),
    authority_type: str | None = Query(
        default=None,
        description="Filter authorities by authority type.",
    ),
    is_active: bool | None = Query(
        default=None,
        description="Filter authorities by active status.",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of records to skip.",
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
        description="Maximum number of records to return.",
    ),
):
    authorities, total = list_authorities(
        db=db,
        search=search,
        department_id=department_id,
        authority_type=authority_type,
        is_active=is_active,
        offset=offset,
        limit=limit,
    )

    return AuthorityListResponse(
        items=authorities,
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/{authority_id}",
    response_model=AuthorityResponse,
    status_code=status.HTTP_200_OK,
)
def get_managed_authority(
    authority_id: UUID,
    db: Session = Depends(get_db),
    current_user: AuthorityReader = None,
):
    authority = get_authority(
        db=db,
        authority_id=authority_id,
    )

    if authority is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Authority not found.",
        )

    return authority


@router.post(
    "",
    response_model=AuthorityResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_managed_authority(
    payload: CreateAuthorityRequest,
    db: Session = Depends(get_db),
    current_user: SystemAdministrator = None,
):
    try:
        return create_authority(
            db=db,
            department_id=payload.department_id,
            code=payload.code,
            name=payload.name,
            authority_type=payload.authority_type,
            description=payload.description,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.patch(
    "/{authority_id}",
    response_model=AuthorityResponse,
    status_code=status.HTTP_200_OK,
)
def update_managed_authority(
    authority_id: UUID,
    payload: UpdateAuthorityRequest,
    db: Session = Depends(get_db),
    current_user: SystemAdministrator = None,
):
    try:
        return update_authority(
            db=db,
            authority_id=authority_id,
            department_id=payload.department_id,
            code=payload.code,
            name=payload.name,
            authority_type=payload.authority_type,
            description=payload.description,
        )
    except ValueError as exc:
        status_code = (
            status.HTTP_404_NOT_FOUND
            if str(exc) == "Authority not found."
            else status.HTTP_400_BAD_REQUEST
        )

        raise HTTPException(
            status_code=status_code,
            detail=str(exc),
        ) from exc


@router.patch(
    "/{authority_id}/status",
    response_model=AuthorityResponse,
    status_code=status.HTTP_200_OK,
)
def update_managed_authority_status(
    authority_id: UUID,
    payload: UpdateAuthorityStatusRequest,
    db: Session = Depends(get_db),
    current_user: SystemAdministrator = None,
):
    try:
        return set_authority_active_status(
            db=db,
            authority_id=authority_id,
            is_active=payload.is_active,
        )
    except ValueError as exc:
        status_code = (
            status.HTTP_404_NOT_FOUND
            if str(exc) == "Authority not found."
            else status.HTTP_400_BAD_REQUEST
        )

        raise HTTPException(
            status_code=status_code,
            detail=str(exc),
        ) from exc
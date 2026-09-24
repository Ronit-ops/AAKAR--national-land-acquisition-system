from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.land_requirements import (
    CreateLandRequirementRequest,
    LandRequirementActionRequest,
    LandRequirementListResponse,
    LandRequirementResponse,
    LandRequirementStatusResponse,
    UpdateLandRequirementRequest,
)
from app.services.land_requirement_service import (
    approve_land_requirement,
    create_land_requirement,
    get_land_requirement,
    list_land_requirements,
    reject_land_requirement,
    submit_land_requirement,
    update_land_requirement,
    withdraw_land_requirement,
)


router = APIRouter(
    prefix="/land-requirements",
    tags=["Land Requirements"],
)


def _land_requirement_response(
    land_requirement,
) -> LandRequirementResponse:
    """Convert a Land Requirement model into the public API response."""

    return LandRequirementResponse(
        id=land_requirement.id,
        project_id=land_requirement.project_id,
        requirement_reference=land_requirement.requirement_reference,
        purpose=land_requirement.purpose,
        required_area_sq_m=land_requirement.required_area_sq_m,
        state=land_requirement.state,
        district=land_requirement.district,
        taluka=land_requirement.taluka,
        village=land_requirement.village,
        description=land_requirement.description,
        status=land_requirement.status,
        created_at=land_requirement.created_at,
        updated_at=land_requirement.updated_at,
    )


@router.get(
    "",
    response_model=LandRequirementListResponse,
    status_code=status.HTTP_200_OK,
)
def list_land_requirement_records(
    search: str | None = Query(
        default=None,
        max_length=200,
    ),
    status_filter: str | None = Query(
        default=None,
        alias="status",
        max_length=30,
    ),
    project_id: UUID | None = Query(
        default=None,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(
        require_permission("land_requirement.read")
    ),
):
    """List and search Land Requirements."""

    try:
        requirements, total = list_land_requirements(
            db=db,
            search=search,
            status=status_filter,
            project_id=project_id,
            offset=offset,
            limit=limit,
        )

        return LandRequirementListResponse(
            items=[
                _land_requirement_response(requirement)
                for requirement in requirements
            ],
            total=total,
            offset=offset,
            limit=limit,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/{land_requirement_id}",
    response_model=LandRequirementResponse,
    status_code=status.HTTP_200_OK,
)
def get_land_requirement_record(
    land_requirement_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(
        require_permission("land_requirement.read")
    ),
):
    """Return one Land Requirement by ID."""

    land_requirement = get_land_requirement(
        db=db,
        land_requirement_id=land_requirement_id,
    )

    if land_requirement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Land Requirement not found.",
        )

    return _land_requirement_response(
        land_requirement
    )


@router.post(
    "",
    response_model=LandRequirementResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_land_requirement_record(
    payload: CreateLandRequirementRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(
        require_permission("land_requirement.create")
    ),
):
    """Create a new Land Requirement in DRAFT status."""

    try:
        land_requirement = create_land_requirement(
            db=db,
            project_id=payload.project_id,
            requirement_reference=payload.requirement_reference,
            purpose=payload.purpose,
            required_area_sq_m=payload.required_area_sq_m,
            state=payload.state,
            district=payload.district,
            taluka=payload.taluka,
            village=payload.village,
            description=payload.description,
            actor_user_id=current_user.id,
        )

        return _land_requirement_response(
            land_requirement
        )

    except ValueError as exc:
        message = str(exc)

        if "already exists" in message:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=message,
            ) from exc

        if message == "Project not found.":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=message,
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        ) from exc

    except IntegrityError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Land Requirement could not be created "
                "because of a conflicting record."
            ),
        ) from exc


@router.put(
    "/{land_requirement_id}",
    response_model=LandRequirementResponse,
    status_code=status.HTTP_200_OK,
)
def update_land_requirement_record(
    land_requirement_id: UUID,
    payload: UpdateLandRequirementRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(
        require_permission("land_requirement.update")
    ),
):
    """Update an editable Land Requirement."""

    try:
        land_requirement = update_land_requirement(
            db=db,
            land_requirement_id=land_requirement_id,
            requirement_reference=payload.requirement_reference,
            purpose=payload.purpose,
            required_area_sq_m=payload.required_area_sq_m,
            state=payload.state,
            district=payload.district,
            taluka=payload.taluka,
            village=payload.village,
            description=payload.description,
            actor_user_id=current_user.id,
        )

        return _land_requirement_response(
            land_requirement
        )

    except ValueError as exc:
        message = str(exc)

        if message == "Land Requirement not found.":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=message,
            ) from exc

        if "already exists" in message:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=message,
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        ) from exc

    except IntegrityError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Land Requirement could not be updated "
                "because of a conflicting record."
            ),
        ) from exc


@router.post(
    "/{land_requirement_id}/submit",
    response_model=LandRequirementStatusResponse,
    status_code=status.HTTP_200_OK,
)
def submit_land_requirement_record(
    land_requirement_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(
        require_permission("land_requirement.submit")
    ),
):
    """Submit a draft or rejected Land Requirement for review."""

    try:
        land_requirement = submit_land_requirement(
            db=db,
            land_requirement_id=land_requirement_id,
            actor_user_id=current_user.id,
        )

        return LandRequirementStatusResponse(
            id=land_requirement.id,
            status=land_requirement.status,
        )

    except ValueError as exc:
        message = str(exc)

        if message == "Land Requirement not found.":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=message,
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        ) from exc


@router.post(
    "/{land_requirement_id}/approve",
    response_model=LandRequirementStatusResponse,
    status_code=status.HTTP_200_OK,
)
def approve_land_requirement_record(
    land_requirement_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(
        require_permission("land_requirement.review")
    ),
):
    """Approve a Land Requirement under review."""

    try:
        land_requirement = approve_land_requirement(
            db=db,
            land_requirement_id=land_requirement_id,
            actor_user_id=current_user.id,
        )

        return LandRequirementStatusResponse(
            id=land_requirement.id,
            status=land_requirement.status,
        )

    except ValueError as exc:
        message = str(exc)

        if message == "Land Requirement not found.":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=message,
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        ) from exc


@router.post(
    "/{land_requirement_id}/reject",
    response_model=LandRequirementStatusResponse,
    status_code=status.HTTP_200_OK,
)
def reject_land_requirement_record(
    land_requirement_id: UUID,
    payload: LandRequirementActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(
        require_permission("land_requirement.review")
    ),
):
    """Reject a Land Requirement under review."""

    try:
        land_requirement = reject_land_requirement(
            db=db,
            land_requirement_id=land_requirement_id,
            actor_user_id=current_user.id,
            reason=payload.reason,
        )

        return LandRequirementStatusResponse(
            id=land_requirement.id,
            status=land_requirement.status,
        )

    except ValueError as exc:
        message = str(exc)

        if message == "Land Requirement not found.":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=message,
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        ) from exc


@router.post(
    "/{land_requirement_id}/withdraw",
    response_model=LandRequirementStatusResponse,
    status_code=status.HTTP_200_OK,
)
def withdraw_land_requirement_record(
    land_requirement_id: UUID,
    payload: LandRequirementActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(
        require_permission("land_requirement.withdraw")
    ),
):
    """Withdraw an eligible Land Requirement."""

    try:
        land_requirement = withdraw_land_requirement(
            db=db,
            land_requirement_id=land_requirement_id,
            actor_user_id=current_user.id,
            reason=payload.reason,
        )

        return LandRequirementStatusResponse(
            id=land_requirement.id,
            status=land_requirement.status,
        )

    except ValueError as exc:
        message = str(exc)

        if message == "Land Requirement not found.":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=message,
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        ) from exc
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.parcels import (
    CreateParcelRequest,
    ParcelListResponse,
    ParcelResponse,
    UpdateParcelRequest,
)
from app.services.parcel_service import (
    create_parcel,
    get_parcel,
    list_parcels,
    update_parcel,
)


router = APIRouter(
    prefix="/parcels",
    tags=["Parcels"],
)


def _parcel_response(parcel) -> ParcelResponse:
    return ParcelResponse(
        id=parcel.id,
        parcel_reference=parcel.parcel_reference,
        state=parcel.state,
        district=parcel.district,
        taluka=parcel.taluka,
        village=parcel.village,
        survey_number=parcel.survey_number,
        subdivision_number=parcel.subdivision_number,
        recorded_area_sq_m=parcel.recorded_area_sq_m,
        surveyed_area_sq_m=parcel.surveyed_area_sq_m,
        acquired_area_sq_m=parcel.acquired_area_sq_m,
        land_category=parcel.land_category,
        land_record_reference=parcel.land_record_reference,
        source_system=parcel.source_system,
        geometry=None,
        created_at=parcel.created_at,
        updated_at=parcel.updated_at,
    )


@router.get(
    "",
    response_model=ParcelListResponse,
)
def get_parcels(
    search: str | None = Query(
        default=None,
        max_length=100,
    ),
    state: str | None = Query(
        default=None,
        max_length=100,
    ),
    district: str | None = Query(
        default=None,
        max_length=100,
    ),
    taluka: str | None = Query(
        default=None,
        max_length=100,
    ),
    village: str | None = Query(
        default=None,
        max_length=100,
    ),
    survey_number: str | None = Query(
        default=None,
        max_length=100,
    ),
    land_category: str | None = Query(
        default=None,
        max_length=100,
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
    current_user: User = Depends(
        require_permission("parcel.read")
    ),
    db: Session = Depends(get_db),
) -> ParcelListResponse:
    parcels, total = list_parcels(
        db,
        search=search,
        state=state,
        district=district,
        taluka=taluka,
        village=village,
        survey_number=survey_number,
        land_category=land_category,
        offset=offset,
        limit=limit,
    )

    return ParcelListResponse(
        items=[
            _parcel_response(parcel)
            for parcel in parcels
        ],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/{parcel_id}",
    response_model=ParcelResponse,
)
def get_parcel_by_id(
    parcel_id: UUID,
    current_user: User = Depends(
        require_permission("parcel.read")
    ),
    db: Session = Depends(get_db),
) -> ParcelResponse:
    parcel = get_parcel(
        db,
        parcel_id,
    )

    if parcel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parcel not found.",
        )

    return _parcel_response(parcel)


@router.post(
    "",
    response_model=ParcelResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_parcel_endpoint(
    payload: CreateParcelRequest,
    current_user: User = Depends(
        require_permission("parcel.create")
    ),
    db: Session = Depends(get_db),
) -> ParcelResponse:
    try:
        parcel = create_parcel(
            db,
            parcel_reference=payload.parcel_reference,
            state=payload.state,
            district=payload.district,
            taluka=payload.taluka,
            village=payload.village,
            survey_number=payload.survey_number,
            subdivision_number=payload.subdivision_number,
            recorded_area_sq_m=payload.recorded_area_sq_m,
            surveyed_area_sq_m=payload.surveyed_area_sq_m,
            acquired_area_sq_m=payload.acquired_area_sq_m,
            land_category=payload.land_category,
            land_record_reference=payload.land_record_reference,
            source_system=payload.source_system,
            actor_user_id=current_user.id,
        )

        return _parcel_response(parcel)

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Unable to create the Parcel because "
                "the record conflicts with existing data."
            ),
        ) from exc


@router.put(
    "/{parcel_id}",
    response_model=ParcelResponse,
)
def update_parcel_endpoint(
    parcel_id: UUID,
    payload: UpdateParcelRequest,
    current_user: User = Depends(
        require_permission("parcel.update")
    ),
    db: Session = Depends(get_db),
) -> ParcelResponse:
    try:
        parcel = update_parcel(
            db,
            parcel_id=parcel_id,
            parcel_reference=payload.parcel_reference,
            state=payload.state,
            district=payload.district,
            taluka=payload.taluka,
            village=payload.village,
            survey_number=payload.survey_number,
            subdivision_number=payload.subdivision_number,
            recorded_area_sq_m=payload.recorded_area_sq_m,
            surveyed_area_sq_m=payload.surveyed_area_sq_m,
            acquired_area_sq_m=payload.acquired_area_sq_m,
            land_category=payload.land_category,
            land_record_reference=payload.land_record_reference,
            source_system=payload.source_system,
            actor_user_id=current_user.id,
        )

        return _parcel_response(parcel)

    except ValueError as exc:
        if str(exc) == "Parcel not found.":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(exc),
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Unable to update the Parcel because "
                "the record conflicts with existing data."
            ),
        ) from exc
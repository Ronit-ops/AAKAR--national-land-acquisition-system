from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.acquisition_cases import (
    AcquisitionCaseActivate,
    AcquisitionCaseCancel,
    AcquisitionCaseClose,
    AcquisitionCaseCreate,
    AcquisitionCaseDetail,
    AcquisitionCaseHold,
    AcquisitionCaseListResponse,
    AcquisitionCaseRead,
    AcquisitionCaseResume,
    AcquisitionCaseStageHistoryRead,
    AcquisitionCaseStageTransition,
    AcquisitionCaseUpdate,
)
from app.services import acquisition_case_service


router = APIRouter(
    prefix="/acquisition-cases",
    tags=["Acquisition Cases"],
)


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=AcquisitionCaseListResponse,
    dependencies=[Depends(require_permission("acquisition_case.read"))],
)
def list_acquisition_cases(
    search: str | None = Query(
        default=None,
        max_length=200,
    ),
    status: str | None = Query(
        default=None,
        max_length=20,
    ),
    current_stage: str | None = Query(
        default=None,
        max_length=50,
    ),
    legal_framework: str | None = Query(
        default=None,
        max_length=40,
    ),
    acquisition_method: str | None = Query(
        default=None,
        max_length=40,
    ),
    land_requirement_id: UUID | None = Query(default=None),
    responsible_authority_id: UUID | None = Query(default=None),
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
) -> AcquisitionCaseListResponse:
    try:
        cases, total = acquisition_case_service.list_acquisition_cases(
            db,
            search=search,
            status=status,
            current_stage=current_stage,
            legal_framework=legal_framework,
            acquisition_method=acquisition_method,
            land_requirement_id=land_requirement_id,
            responsible_authority_id=responsible_authority_id,
            offset=offset,
            limit=limit,
        )

        return AcquisitionCaseListResponse(
            items=cases,
            total=total,
            offset=offset,
            limit=limit,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ---------------------------------------------------------------------------
# Detail
# ---------------------------------------------------------------------------


@router.get(
    "/{acquisition_case_id}",
    response_model=AcquisitionCaseDetail,
    dependencies=[Depends(require_permission("acquisition_case.read"))],
)
def get_acquisition_case(
    acquisition_case_id: UUID,
    db: Session = Depends(get_db),
) -> AcquisitionCaseDetail:
    try:
        return acquisition_case_service.get_acquisition_case(
            db,
            acquisition_case_id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=AcquisitionCaseRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("acquisition_case.create"))],
)
def create_acquisition_case(
    payload: AcquisitionCaseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AcquisitionCaseRead:
    try:
        return acquisition_case_service.create_acquisition_case(
            db,
            land_requirement_id=payload.land_requirement_id,
            case_number=payload.case_number,
            legal_framework=payload.legal_framework,
            legal_route=payload.legal_route,
            acquisition_method=payload.acquisition_method,
            responsible_authority_id=payload.responsible_authority_id,
            assigned_user_id=payload.assigned_user_id,
            description=payload.description,
            actor_user_id=current_user.id,
        )

    except ValueError as exc:
        detail = str(exc)

        if "already exists" in detail:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=detail,
            ) from exc

        if "not found" in detail.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=detail,
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        ) from exc

    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Acquisition Case could not be created because of a database conflict.",
        ) from exc


# ---------------------------------------------------------------------------
# Update metadata
# ---------------------------------------------------------------------------


@router.put(
    "/{acquisition_case_id}",
    response_model=AcquisitionCaseRead,
    dependencies=[Depends(require_permission("acquisition_case.update"))],
)
def update_acquisition_case(
    acquisition_case_id: UUID,
    payload: AcquisitionCaseUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AcquisitionCaseRead:
    update_fields = payload.model_fields_set

    try:
        return acquisition_case_service.update_acquisition_case(
            db,
            acquisition_case_id=acquisition_case_id,
            actor_user_id=current_user.id,
            expected_version=payload.expected_version,
            legal_framework=payload.legal_framework,
            legal_route=payload.legal_route,
            acquisition_method=payload.acquisition_method,
            responsible_authority_id=payload.responsible_authority_id,
            assigned_user_id=payload.assigned_user_id,
            description=payload.description,
            update_fields=update_fields,
        )

    except ValueError as exc:
        detail = str(exc)

        if "not found" in detail.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=detail,
            ) from exc

        if "modified by another user" in detail.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=detail,
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        ) from exc

    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Acquisition Case could not be updated because of a database conflict.",
        ) from exc


# ---------------------------------------------------------------------------
# Activate
# ---------------------------------------------------------------------------


@router.post(
    "/{acquisition_case_id}/activate",
    response_model=AcquisitionCaseRead,
    dependencies=[Depends(require_permission("acquisition_case.activate"))],
)
def activate_acquisition_case(
    acquisition_case_id: UUID,
    payload: AcquisitionCaseActivate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AcquisitionCaseRead:
    try:
        return acquisition_case_service.activate_acquisition_case(
            db,
            acquisition_case_id=acquisition_case_id,
            actor_user_id=current_user.id,
            expected_version=payload.expected_version,
        )

    except ValueError as exc:
        detail = str(exc)

        if "not found" in detail.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=detail,
            ) from exc

        if "modified by another user" in detail.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=detail,
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        ) from exc


# ---------------------------------------------------------------------------
# Hold
# ---------------------------------------------------------------------------


@router.post(
    "/{acquisition_case_id}/hold",
    response_model=AcquisitionCaseRead,
    dependencies=[Depends(require_permission("acquisition_case.hold"))],
)
def hold_acquisition_case(
    acquisition_case_id: UUID,
    payload: AcquisitionCaseHold,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AcquisitionCaseRead:
    try:
        return acquisition_case_service.hold_acquisition_case(
            db,
            acquisition_case_id=acquisition_case_id,
            reason=payload.reason,
            actor_user_id=current_user.id,
            expected_version=payload.expected_version,
        )

    except ValueError as exc:
        detail = str(exc)

        if "not found" in detail.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=detail,
            ) from exc

        if "modified by another user" in detail.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=detail,
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        ) from exc


# ---------------------------------------------------------------------------
# Resume
# ---------------------------------------------------------------------------


@router.post(
    "/{acquisition_case_id}/resume",
    response_model=AcquisitionCaseRead,
    dependencies=[Depends(require_permission("acquisition_case.resume"))],
)
def resume_acquisition_case(
    acquisition_case_id: UUID,
    payload: AcquisitionCaseResume,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AcquisitionCaseRead:
    try:
        return acquisition_case_service.resume_acquisition_case(
            db,
            acquisition_case_id=acquisition_case_id,
            actor_user_id=current_user.id,
            expected_version=payload.expected_version,
        )

    except ValueError as exc:
        detail = str(exc)

        if "not found" in detail.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=detail,
            ) from exc

        if "modified by another user" in detail.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=detail,
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        ) from exc


# ---------------------------------------------------------------------------
# Cancel
# ---------------------------------------------------------------------------


@router.post(
    "/{acquisition_case_id}/cancel",
    response_model=AcquisitionCaseRead,
    dependencies=[Depends(require_permission("acquisition_case.cancel"))],
)
def cancel_acquisition_case(
    acquisition_case_id: UUID,
    payload: AcquisitionCaseCancel,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AcquisitionCaseRead:
    try:
        return acquisition_case_service.cancel_acquisition_case(
            db,
            acquisition_case_id=acquisition_case_id,
            reason=payload.reason,
            actor_user_id=current_user.id,
            expected_version=payload.expected_version,
        )

    except ValueError as exc:
        detail = str(exc)

        if "not found" in detail.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=detail,
            ) from exc

        if "modified by another user" in detail.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=detail,
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        ) from exc


# ---------------------------------------------------------------------------
# Close
# ---------------------------------------------------------------------------


@router.post(
    "/{acquisition_case_id}/close",
    response_model=AcquisitionCaseRead,
    dependencies=[Depends(require_permission("acquisition_case.close"))],
)
def close_acquisition_case(
    acquisition_case_id: UUID,
    payload: AcquisitionCaseClose,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AcquisitionCaseRead:
    try:
        return acquisition_case_service.close_acquisition_case(
            db,
            acquisition_case_id=acquisition_case_id,
            actor_user_id=current_user.id,
            expected_version=payload.expected_version,
        )

    except ValueError as exc:
        detail = str(exc)

        if "not found" in detail.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=detail,
            ) from exc

        if "modified by another user" in detail.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=detail,
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        ) from exc


# ---------------------------------------------------------------------------
# Stage transition
# ---------------------------------------------------------------------------


@router.post(
    "/{acquisition_case_id}/stage-transition",
    response_model=AcquisitionCaseRead,
    dependencies=[
        Depends(require_permission("acquisition_case.stage_transition"))
    ],
)
def transition_acquisition_case_stage(
    acquisition_case_id: UUID,
    payload: AcquisitionCaseStageTransition,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AcquisitionCaseRead:
    try:
        return acquisition_case_service.transition_acquisition_case_stage(
            db,
            acquisition_case_id=acquisition_case_id,
            to_stage=payload.to_stage,
            reason=payload.reason,
            actor_user_id=current_user.id,
            expected_version=payload.expected_version,
        )

    except ValueError as exc:
        detail = str(exc)

        if "not found" in detail.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=detail,
            ) from exc

        if "modified by another user" in detail.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=detail,
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        ) from exc


# ---------------------------------------------------------------------------
# Stage history
# ---------------------------------------------------------------------------


@router.get(
    "/{acquisition_case_id}/stage-history",
    response_model=list[AcquisitionCaseStageHistoryRead],
    dependencies=[Depends(require_permission("acquisition_case.read"))],
)
def list_acquisition_case_stage_history(
    acquisition_case_id: UUID,
    db: Session = Depends(get_db),
) -> list[AcquisitionCaseStageHistoryRead]:
    try:
        return acquisition_case_service.list_stage_history(
            db,
            acquisition_case_id=acquisition_case_id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

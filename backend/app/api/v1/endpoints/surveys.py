from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.db.session import get_db
from app.models.survey_record import SURVEY_STATUSES
from app.models.user import User
from app.schemas.surveys import (
    SurveyRecordCompleteRequest,
    SurveyRecordCreateRequest,
    SurveyRecordListResponse,
    SurveyRecordResponse,
)
from app.services.survey_service import (
    cancel_survey,
    complete_survey,
    create_survey_record,
    get_survey_record,
    list_survey_records,
    send_survey_for_review,
    start_survey,
    verify_survey,
)


router = APIRouter(
    prefix="/surveys",
    tags=["Surveys"],
)


@router.get(
    "",
    response_model=SurveyRecordListResponse,
)
def get_surveys(
    acquisition_case_id: UUID | None = Query(default=None),
    parcel_id: UUID | None = Query(default=None),
    survey_status: str | None = Query(
        default=None,
        alias="status",
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=200,
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permission("survey.read")
    ),
):
    del current_user

    try:
        surveys = list_survey_records(
            db,
            acquisition_case_id=acquisition_case_id,
            parcel_id=parcel_id,
            status=survey_status,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    total = len(surveys)

    paginated_surveys = surveys[
        offset : offset + limit
    ]

    return SurveyRecordListResponse(
        items=[
            SurveyRecordResponse.model_validate(survey)
            for survey in paginated_surveys
        ],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/{survey_id}",
    response_model=SurveyRecordResponse,
)
def get_survey(
    survey_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permission("survey.read")
    ),
):
    del current_user

    survey = get_survey_record(
        db,
        survey_id,
    )

    if survey is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Survey record not found.",
        )

    return SurveyRecordResponse.model_validate(survey)


@router.post(
    "",
    response_model=SurveyRecordResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_survey(
    payload: SurveyRecordCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permission("survey.create")
    ),
):
    try:
        survey = create_survey_record(
            db,
            acquisition_case_id=payload.acquisition_case_id,
            parcel_id=payload.parcel_id,
            survey_reference=payload.survey_reference,
            survey_type=payload.survey_type,
            survey_method=payload.survey_method,
            scheduled_at=payload.scheduled_at,
            surveyor_user_id=payload.surveyor_user_id,
            notes=payload.notes,
            actor_user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return SurveyRecordResponse.model_validate(survey)


@router.post(
    "/{survey_id}/start",
    response_model=SurveyRecordResponse,
)
def start_survey_record(
    survey_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permission("survey.start")
    ),
):
    try:
        survey = start_survey(
            db,
            survey_id=survey_id,
            actor_user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return SurveyRecordResponse.model_validate(survey)


@router.post(
    "/{survey_id}/complete",
    response_model=SurveyRecordResponse,
)
def complete_survey_record(
    survey_id: UUID,
    payload: SurveyRecordCompleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permission("survey.complete")
    ),
):
    try:
        survey = complete_survey(
            db,
            survey_id=survey_id,
            measured_area_sq_m=payload.measured_area_sq_m,
            conducted_at=payload.conducted_at,
            actor_user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return SurveyRecordResponse.model_validate(survey)


@router.post(
    "/{survey_id}/review",
    response_model=SurveyRecordResponse,
)
def review_survey_record(
    survey_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permission("survey.review")
    ),
):
    try:
        survey = send_survey_for_review(
            db,
            survey_id=survey_id,
            actor_user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return SurveyRecordResponse.model_validate(survey)


@router.post(
    "/{survey_id}/verify",
    response_model=SurveyRecordResponse,
)
def verify_survey_record(
    survey_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permission("survey.verify")
    ),
):
    try:
        survey = verify_survey(
            db,
            survey_id=survey_id,
            verifier_user_id=current_user.id,
            actor_user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return SurveyRecordResponse.model_validate(survey)


@router.post(
    "/{survey_id}/cancel",
    response_model=SurveyRecordResponse,
)
def cancel_survey_record(
    survey_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_permission("survey.cancel")
    ),
):
    try:
        survey = cancel_survey(
            db,
            survey_id=survey_id,
            actor_user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return SurveyRecordResponse.model_validate(survey)
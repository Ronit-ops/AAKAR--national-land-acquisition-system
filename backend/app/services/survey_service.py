from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.acquisition_case import AcquisitionCase
from app.models.case_parcel import CaseParcel
from app.models.parcel import Parcel
from app.models.survey_record import (
    SURVEY_STATUSES,
    SURVEY_TYPES,
    SurveyRecord,
)
from app.models.user import User
from app.services.audit_service import record_audit_event


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

AREA_DECIMAL_PLACES = Decimal("0.0001")
PERCENTAGE_DECIMAL_PLACES = Decimal("0.000001")

FINAL_SURVEY_STATUSES = {
    "COMPLETED",
    "REQUIRES_REVIEW",
    "VERIFIED",
    "CANCELLED",
}

VERIFICATION_REQUIRED_STATUSES = {
    "VERIFIED",
}

CONDUCTED_REQUIRED_STATUSES = {
    "COMPLETED",
    "REQUIRES_REVIEW",
    "VERIFIED",
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _utc_now() -> datetime:
    """Return the current timezone-aware UTC timestamp."""

    return datetime.now(timezone.utc)


def _normalize_decimal(
    value: Decimal,
    places: Decimal,
) -> Decimal:
    """Round a Decimal value to the required database precision."""

    return value.quantize(
        places,
        rounding=ROUND_HALF_UP,
    )


def _calculate_area_difference(
    *,
    recorded_area_sq_m: Decimal,
    measured_area_sq_m: Decimal | None,
) -> tuple[Decimal | None, Decimal | None]:
    """
    Calculate absolute area difference and percentage difference.

    Difference:
        measured - recorded

    Percentage:
        ((measured - recorded) / recorded) * 100
    """

    if measured_area_sq_m is None:
        return None, None

    difference = measured_area_sq_m - recorded_area_sq_m

    percentage = (
        difference / recorded_area_sq_m
    ) * Decimal("100")

    return (
        _normalize_decimal(
            difference,
            AREA_DECIMAL_PLACES,
        ),
        _normalize_decimal(
            percentage,
            PERCENTAGE_DECIMAL_PLACES,
        ),
    )


def _get_case(
    db: Session,
    acquisition_case_id: UUID,
) -> AcquisitionCase:
    """Load an acquisition case or raise a domain error."""

    case = db.scalar(
        select(AcquisitionCase).where(
            AcquisitionCase.id == acquisition_case_id,
        )
    )

    if case is None:
        raise ValueError("Acquisition case not found.")

    return case


def _get_parcel(
    db: Session,
    parcel_id: UUID,
) -> Parcel:
    """Load a parcel or raise a domain error."""

    parcel = db.scalar(
        select(Parcel).where(
            Parcel.id == parcel_id,
        )
    )

    if parcel is None:
        raise ValueError("Parcel not found.")

    return parcel


def _ensure_case_parcel_link(
    db: Session,
    *,
    acquisition_case_id: UUID,
    parcel_id: UUID,
) -> CaseParcel:
    """
    Ensure that the parcel is actually associated with the acquisition case.
    """

    case_parcel = db.scalar(
        select(CaseParcel).where(
            CaseParcel.acquisition_case_id
            == acquisition_case_id,
            CaseParcel.parcel_id == parcel_id,
            CaseParcel.inclusion_status == "ACTIVE",
        )
    )

    if case_parcel is None:
        raise ValueError(
            "The parcel is not actively associated with "
            "the acquisition case."
        )

    return case_parcel


def _get_user(
    db: Session,
    user_id: UUID,
) -> User:
    """Load a user or raise a domain error."""

    user = db.scalar(
        select(User).where(
            User.id == user_id,
        )
    )

    if user is None:
        raise ValueError("User not found.")

    return user


def _get_survey(
    db: Session,
    survey_id: UUID,
) -> SurveyRecord:
    """Load a survey record or raise a domain error."""

    survey = db.scalar(
        select(SurveyRecord).where(
            SurveyRecord.id == survey_id,
        )
    )

    if survey is None:
        raise ValueError("Survey record not found.")

    return survey


def _ensure_status_transition(
    *,
    current_status: str,
    new_status: str,
) -> None:
    """
    Validate the supported survey lifecycle transitions.

    PLANNED
        -> IN_PROGRESS
        -> CANCELLED

    IN_PROGRESS
        -> COMPLETED
        -> REQUIRES_REVIEW
        -> CANCELLED

    COMPLETED
        -> REQUIRES_REVIEW

    REQUIRES_REVIEW
        -> VERIFIED

    VERIFIED
        -> no further transition

    CANCELLED
        -> no further transition
    """

    allowed_transitions: dict[str, set[str]] = {
        "PLANNED": {
            "IN_PROGRESS",
            "CANCELLED",
        },
        "IN_PROGRESS": {
            "COMPLETED",
            "REQUIRES_REVIEW",
            "CANCELLED",
        },
        "COMPLETED": {
            "REQUIRES_REVIEW",
        },
        "REQUIRES_REVIEW": {
            "VERIFIED",
        },
        "VERIFIED": set(),
        "CANCELLED": set(),
    }

    if new_status not in allowed_transitions.get(
        current_status,
        set(),
    ):
        raise ValueError(
            f"Invalid survey status transition: "
            f"{current_status} -> {new_status}."
        )


# ---------------------------------------------------------------------------
# Create survey
# ---------------------------------------------------------------------------


def create_survey_record(
    db: Session,
    *,
    acquisition_case_id: UUID,
    parcel_id: UUID,
    survey_reference: str,
    survey_type: str,
    survey_method: str,
    scheduled_at: datetime | None = None,
    surveyor_user_id: UUID | None = None,
    notes: str | None = None,
    actor_user_id: UUID | None = None,
    commit: bool = True,
) -> SurveyRecord:
    """
    Create a new survey record.

    A survey can only be created for a parcel that is actively linked
    to the specified acquisition case.
    """

    survey_reference = survey_reference.strip()

    if not survey_reference:
        raise ValueError(
            "Survey reference must not be empty."
        )

    if survey_type not in SURVEY_TYPES:
        raise ValueError(
            f"Invalid survey type: {survey_type}."
        )

    if survey_method not in (
        "FIELD_SURVEY",
        "GNSS",
        "TOTAL_STATION",
        "GPS",
        "DIGITIZED",
        "OTHER",
    ):
        raise ValueError(
            f"Invalid survey method: {survey_method}."
        )

    case = _get_case(
        db,
        acquisition_case_id,
    )

    parcel = _get_parcel(
        db,
        parcel_id,
    )

    _ensure_case_parcel_link(
        db,
        acquisition_case_id=acquisition_case_id,
        parcel_id=parcel_id,
    )

    if surveyor_user_id is not None:
        _get_user(
            db,
            surveyor_user_id,
        )

    if case.status in {
        "CANCELLED",
        "CLOSED",
    }:
        raise ValueError(
            "A survey cannot be created for a "
            f"{case.status.lower()} acquisition case."
        )

    if parcel.recorded_area_sq_m is None:
        raise ValueError(
            "Parcel recorded area is required before "
            "creating a survey."
        )

    existing = db.scalar(
        select(SurveyRecord).where(
            SurveyRecord.acquisition_case_id
            == acquisition_case_id,
            SurveyRecord.survey_reference
            == survey_reference,
        )
    )

    if existing is not None:
        raise ValueError(
            "A survey with this reference already exists "
            "for the acquisition case."
        )

    survey = SurveyRecord(
        acquisition_case_id=acquisition_case_id,
        parcel_id=parcel_id,
        survey_reference=survey_reference,
        survey_type=survey_type,
        survey_method=survey_method,
        status="PLANNED",
        scheduled_at=scheduled_at,
        surveyor_user_id=surveyor_user_id,
        recorded_area_sq_m=parcel.recorded_area_sq_m,
        notes=notes.strip() if notes else None,
    )

    db.add(survey)

    try:
        db.flush()

        record_audit_event(
            db,
            actor_user_id=actor_user_id,
            action="survey_record_created",
            entity_type="survey_record",
            entity_id=survey.id,
            result="success",
            details={
                "acquisition_case_id": str(
                    acquisition_case_id
                ),
                "parcel_id": str(parcel_id),
                "survey_reference": survey_reference,
                "survey_type": survey_type,
                "survey_method": survey_method,
            },
            commit=False,
        )

        if commit:
            db.commit()
            db.refresh(survey)

        return survey

    except IntegrityError as exc:
        db.rollback()

        raise ValueError(
            "Unable to create the survey record because "
            "it violates a database constraint."
        ) from exc

    except Exception:
        db.rollback()
        raise


# ---------------------------------------------------------------------------
# Start survey
# ---------------------------------------------------------------------------


def start_survey(
    db: Session,
    *,
    survey_id: UUID,
    actor_user_id: UUID | None = None,
    commit: bool = True,
) -> SurveyRecord:
    """Move a planned survey into field execution."""

    survey = _get_survey(
        db,
        survey_id,
    )

    _ensure_status_transition(
        current_status=survey.status,
        new_status="IN_PROGRESS",
    )

    survey.status = "IN_PROGRESS"

    if survey.surveyor_user_id is None:
        if actor_user_id is None:
            raise ValueError(
                "A surveyor must be assigned before "
                "starting the survey."
            )

        _get_user(
            db,
            actor_user_id,
        )

        survey.surveyor_user_id = actor_user_id

    try:
        db.flush()

        record_audit_event(
            db,
            actor_user_id=actor_user_id,
            action="survey_started",
            entity_type="survey_record",
            entity_id=survey.id,
            result="success",
            details={
                "status": survey.status,
                "surveyor_user_id": str(
                    survey.surveyor_user_id
                ),
            },
            commit=False,
        )

        if commit:
            db.commit()
            db.refresh(survey)

        return survey

    except Exception:
        db.rollback()
        raise


# ---------------------------------------------------------------------------
# Complete / review survey
# ---------------------------------------------------------------------------


def complete_survey(
    db: Session,
    *,
    survey_id: UUID,
    measured_area_sq_m: Decimal,
    conducted_at: datetime | None = None,
    actor_user_id: UUID | None = None,
    commit: bool = True,
) -> SurveyRecord:
    """
    Complete a survey and calculate measurement differences.
    """

    survey = _get_survey(
        db,
        survey_id,
    )

    _ensure_status_transition(
        current_status=survey.status,
        new_status="COMPLETED",
    )

    if measured_area_sq_m <= 0:
        raise ValueError(
            "Measured area must be greater than zero."
        )

    if survey.recorded_area_sq_m <= 0:
        raise ValueError(
            "Recorded area must be greater than zero."
        )

    actual_conducted_at = conducted_at or _utc_now()

    if (
        survey.scheduled_at is not None
        and actual_conducted_at < survey.scheduled_at
    ):
        raise ValueError(
            "Conducted time cannot be earlier than "
            "the scheduled survey time."
        )

    difference, percentage = _calculate_area_difference(
        recorded_area_sq_m=survey.recorded_area_sq_m,
        measured_area_sq_m=measured_area_sq_m,
    )

    survey.measured_area_sq_m = _normalize_decimal(
        measured_area_sq_m,
        AREA_DECIMAL_PLACES,
    )

    survey.area_difference_sq_m = difference
    survey.area_difference_percentage = percentage
    survey.conducted_at = actual_conducted_at
    survey.status = "COMPLETED"

    try:
        db.flush()

        record_audit_event(
            db,
            actor_user_id=actor_user_id,
            action="survey_record_completed",
            entity_type="survey_record",
            entity_id=survey.id,
            result="success",
            details={
                "measured_area_sq_m": str(
                    survey.measured_area_sq_m
                ),
                "area_difference_sq_m": str(
                    survey.area_difference_sq_m
                ),
                "area_difference_percentage": str(
                    survey.area_difference_percentage
                ),
                "conducted_at": (
                    survey.conducted_at.isoformat()
                ),
            },
            commit=False,
        )

        if commit:
            db.commit()
            db.refresh(survey)

        return survey

    except Exception:
        db.rollback()
        raise


def send_survey_for_review(
    db: Session,
    *,
    survey_id: UUID,
    actor_user_id: UUID | None = None,
    commit: bool = True,
) -> SurveyRecord:
    """Move a completed survey into review."""

    survey = _get_survey(
        db,
        survey_id,
    )

    _ensure_status_transition(
        current_status=survey.status,
        new_status="REQUIRES_REVIEW",
    )

    if survey.conducted_at is None:
        raise ValueError(
            "A survey must have a conducted time "
            "before review."
        )

    survey.status = "REQUIRES_REVIEW"

    try:
        db.flush()

        record_audit_event(
            db,
            actor_user_id=actor_user_id,
            action="survey_sent_for_review",
            entity_type="survey_record",
            entity_id=survey.id,
            result="success",
            details={
                "status": survey.status,
            },
            commit=False,
        )

        if commit:
            db.commit()
            db.refresh(survey)

        return survey

    except Exception:
        db.rollback()
        raise


# ---------------------------------------------------------------------------
# Verify survey
# ---------------------------------------------------------------------------


def verify_survey(
    db: Session,
    *,
    survey_id: UUID,
    verifier_user_id: UUID,
    actor_user_id: UUID | None = None,
    commit: bool = True,
) -> SurveyRecord:
    """Verify a survey after review."""

    survey = _get_survey(
        db,
        survey_id,
    )

    _ensure_status_transition(
        current_status=survey.status,
        new_status="VERIFIED",
    )

    if survey.conducted_at is None:
        raise ValueError(
            "A survey must have a conducted time "
            "before verification."
        )

    verifier = _get_user(
        db,
        verifier_user_id,
    )

    if not verifier.is_active:
        raise ValueError(
            "The verifying user is inactive."
        )

    verified_at = _utc_now()

    if verified_at < survey.conducted_at:
        raise ValueError(
            "Verification time cannot be earlier than "
            "the survey conducted time."
        )

    survey.status = "VERIFIED"
    survey.verified_by_user_id = verifier_user_id
    survey.verified_at = verified_at

    try:
        db.flush()

        record_audit_event(
            db,
            actor_user_id=actor_user_id,
            action="survey_record_verified",
            entity_type="survey_record",
            entity_id=survey.id,
            result="success",
            details={
                "verified_by_user_id": str(
                    verifier_user_id
                ),
                "verified_at": verified_at.isoformat(),
            },
            commit=False,
        )

        if commit:
            db.commit()
            db.refresh(survey)

        return survey

    except Exception:
        db.rollback()
        raise


# ---------------------------------------------------------------------------
# Cancel survey
# ---------------------------------------------------------------------------


def cancel_survey(
    db: Session,
    *,
    survey_id: UUID,
    actor_user_id: UUID | None = None,
    commit: bool = True,
) -> SurveyRecord:
    """Cancel a planned or in-progress survey."""

    survey = _get_survey(
        db,
        survey_id,
    )

    _ensure_status_transition(
        current_status=survey.status,
        new_status="CANCELLED",
    )

    survey.status = "CANCELLED"

    try:
        db.flush()

        record_audit_event(
            db,
            actor_user_id=actor_user_id,
            action="survey_record_cancelled",
            entity_type="survey_record",
            entity_id=survey.id,
            result="success",
            details={
                "status": survey.status,
            },
            commit=False,
        )

        if commit:
            db.commit()
            db.refresh(survey)

        return survey

    except Exception:
        db.rollback()
        raise


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------


def get_survey_record(
    db: Session,
    survey_id: UUID,
) -> SurveyRecord | None:
    """Return a survey record by ID."""

    return db.scalar(
        select(SurveyRecord).where(
            SurveyRecord.id == survey_id,
        )
    )


def list_survey_records(
    db: Session,
    *,
    acquisition_case_id: UUID | None = None,
    parcel_id: UUID | None = None,
    status: str | None = None,
) -> list[SurveyRecord]:
    """List survey records using optional filters."""

    statement = select(SurveyRecord).order_by(
        SurveyRecord.created_at.desc()
    )

    if acquisition_case_id is not None:
        statement = statement.where(
            SurveyRecord.acquisition_case_id
            == acquisition_case_id
        )

    if parcel_id is not None:
        statement = statement.where(
            SurveyRecord.parcel_id == parcel_id
        )

    if status is not None:
        if status not in SURVEY_STATUSES:
            raise ValueError(
                f"Invalid survey status: {status}."
            )

        statement = statement.where(
            SurveyRecord.status == status
        )

    return list(
        db.scalars(statement).all()
    )
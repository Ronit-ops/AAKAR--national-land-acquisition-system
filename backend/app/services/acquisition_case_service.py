from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.acquisition_case import (
    ACQUISITION_METHODS,
    CASE_STAGES,
    CASE_STATUSES,
    LEGAL_FRAMEWORKS,
    LEGAL_ROUTES,
    AcquisitionCase,
    AcquisitionCaseStageHistory,
)
from app.models.authority import Authority
from app.models.land_requirement import LandRequirement
from app.models.project import Project
from app.models.user import User
from app.services.audit_service import record_audit_event


# ---------------------------------------------------------------------------
# Controlled values
# ---------------------------------------------------------------------------

CASE_STATUS_DRAFT = "DRAFT"
CASE_STATUS_ACTIVE = "ACTIVE"
CASE_STATUS_ON_HOLD = "ON_HOLD"
CASE_STATUS_CANCELLED = "CANCELLED"
CASE_STATUS_CLOSED = "CLOSED"

CASE_STAGE_INITIATION = "INITIATION"
CASE_STAGE_SIA = "SIA"
CASE_STAGE_PRELIMINARY_NOTIFICATION = "PRELIMINARY_NOTIFICATION"
CASE_STAGE_OBJECTIONS_AND_HEARING = "OBJECTIONS_AND_HEARING"
CASE_STAGE_DECLARATION = "DECLARATION"
CASE_STAGE_R_AND_R = "R_AND_R"
CASE_STAGE_CLAIMS_AND_ENQUIRY = "CLAIMS_AND_ENQUIRY"
CASE_STAGE_COMPENSATION_DETERMINATION = "COMPENSATION_DETERMINATION"
CASE_STAGE_AWARD = "AWARD"
CASE_STAGE_COMPENSATION_AND_RR = "COMPENSATION_AND_RR"
CASE_STAGE_POSSESSION = "POSSESSION"
CASE_STAGE_VESTING = "VESTING"
CASE_STAGE_HANDOVER = "HANDOVER"


# ---------------------------------------------------------------------------
# Stage transition graph
# ---------------------------------------------------------------------------
#
# This is intentionally kept as a domain-level transition graph rather than
# embedding legal-route-specific statutory logic into the service.
#
# Future modules can refine the graph using legal_route / acquisition_method
# without changing the core AcquisitionCase persistence model.
# ---------------------------------------------------------------------------

ALLOWED_STAGE_TRANSITIONS: dict[str, set[str]] = {
    CASE_STAGE_INITIATION: {
        CASE_STAGE_SIA,
        CASE_STAGE_PRELIMINARY_NOTIFICATION,
    },
    CASE_STAGE_SIA: {
        CASE_STAGE_PRELIMINARY_NOTIFICATION,
    },
    CASE_STAGE_PRELIMINARY_NOTIFICATION: {
        CASE_STAGE_OBJECTIONS_AND_HEARING,
    },
    CASE_STAGE_OBJECTIONS_AND_HEARING: {
        CASE_STAGE_DECLARATION,
    },
    CASE_STAGE_DECLARATION: {
        CASE_STAGE_R_AND_R,
        CASE_STAGE_CLAIMS_AND_ENQUIRY,
    },
    CASE_STAGE_R_AND_R: {
        CASE_STAGE_CLAIMS_AND_ENQUIRY,
    },
    CASE_STAGE_CLAIMS_AND_ENQUIRY: {
        CASE_STAGE_COMPENSATION_DETERMINATION,
    },
    CASE_STAGE_COMPENSATION_DETERMINATION: {
        CASE_STAGE_AWARD,
    },
    CASE_STAGE_AWARD: {
        CASE_STAGE_COMPENSATION_AND_RR,
    },
    CASE_STAGE_COMPENSATION_AND_RR: {
        CASE_STAGE_POSSESSION,
    },
    CASE_STAGE_POSSESSION: {
        CASE_STAGE_VESTING,
    },
    CASE_STAGE_VESTING: {
        CASE_STAGE_HANDOVER,
    },
    CASE_STAGE_HANDOVER: set(),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_required_text(
    value: str | None,
    *,
    field_name: str,
) -> str:
    if value is None:
        raise ValueError(f"{field_name} is required.")

    normalized = value.strip()

    if not normalized:
        raise ValueError(f"{field_name} cannot be empty.")

    return normalized


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = value.strip()

    return normalized or None


def _validate_controlled_value(
    value: str | None,
    *,
    allowed_values: set[str] | tuple[str, ...] | list[str],
    field_name: str,
    required: bool = False,
) -> str | None:
    if value is None:
        if required:
            raise ValueError(f"{field_name} is required.")
        return None

    normalized = value.strip().upper()

    if normalized not in allowed_values:
        allowed = ", ".join(sorted(allowed_values))
        raise ValueError(
            f"Invalid {field_name}. Allowed values: {allowed}."
        )

    return normalized


def _get_land_requirement(
    db: Session,
    land_requirement_id: UUID,
) -> LandRequirement:
    land_requirement = db.get(
        LandRequirement,
        land_requirement_id,
    )

    if land_requirement is None:
        raise ValueError("Land Requirement not found.")

    return land_requirement


def _get_project_for_land_requirement(
    db: Session,
    land_requirement: LandRequirement,
) -> Project:
    project = db.get(
        Project,
        land_requirement.project_id,
    )

    if project is None:
        raise ValueError(
            "The Project associated with the Land Requirement was not found."
        )

    return project


def _validate_land_requirement_for_case(
    db: Session,
    land_requirement_id: UUID,
) -> tuple[LandRequirement, Project]:
    land_requirement = _get_land_requirement(
        db,
        land_requirement_id,
    )

    if land_requirement.status != "APPROVED":
        raise ValueError(
            "Only approved Land Requirements can be used to create "
            "an Acquisition Case."
        )

    project = _get_project_for_land_requirement(
        db,
        land_requirement,
    )

    if project.status == "CLOSED":
        raise ValueError(
            "Acquisition Cases cannot be created under a closed Project."
        )

    return land_requirement, project


def _get_acquisition_case(
    db: Session,
    acquisition_case_id: UUID,
) -> AcquisitionCase:
    acquisition_case = db.get(
        AcquisitionCase,
        acquisition_case_id,
    )

    if acquisition_case is None:
        raise ValueError("Acquisition Case not found.")

    return acquisition_case


def _validate_authority(
    db: Session,
    authority_id: UUID | None,
) -> Authority | None:
    if authority_id is None:
        return None

    authority = db.get(
        Authority,
        authority_id,
    )

    if authority is None:
        raise ValueError("Responsible Authority not found.")

    if not authority.is_active:
        raise ValueError("Responsible Authority is inactive.")

    return authority


def _validate_assigned_user(
    db: Session,
    user_id: UUID | None,
) -> User | None:
    if user_id is None:
        return None

    user = db.get(
        User,
        user_id,
    )

    if user is None:
        raise ValueError("Assigned User not found.")

    if not user.is_active:
        raise ValueError("Assigned User is inactive.")

    return user


def _ensure_unique_case_number(
    db: Session,
    case_number: str,
    *,
    exclude_case_id: UUID | None = None,
) -> None:
    statement = select(AcquisitionCase.id).where(
        func.lower(AcquisitionCase.case_number)
        == case_number.lower()
    )

    if exclude_case_id is not None:
        statement = statement.where(
            AcquisitionCase.id != exclude_case_id
        )

    existing_id = db.scalar(statement)

    if existing_id is not None:
        raise ValueError(
            "An Acquisition Case with this case number already exists."
        )


def _validate_version(
    expected_version: int,
) -> None:
    if expected_version < 1:
        raise ValueError(
            "expected_version must be greater than or equal to 1."
        )


def _validate_case_status(
    acquisition_case: AcquisitionCase,
    *,
    allowed_statuses: set[str],
    action: str,
) -> None:
    if acquisition_case.status not in allowed_statuses:
        allowed = ", ".join(sorted(allowed_statuses))
        raise ValueError(
            f"Cannot {action} an Acquisition Case with status "
            f"{acquisition_case.status}. Allowed statuses: {allowed}."
        )


def _validate_stage_transition(
    *,
    current_stage: str,
    target_stage: str,
) -> None:
    if target_stage == current_stage:
        raise ValueError(
            "Acquisition Case is already at the requested stage."
        )

    allowed_targets = ALLOWED_STAGE_TRANSITIONS.get(
        current_stage,
        set(),
    )

    if target_stage not in allowed_targets:
        if allowed_targets:
            allowed = ", ".join(sorted(allowed_targets))
            raise ValueError(
                f"Invalid stage transition from {current_stage} "
                f"to {target_stage}. Allowed next stages: {allowed}."
            )

        raise ValueError(
            f"No stage transitions are allowed from {current_stage}."
        )


def _validate_metadata(
    *,
    legal_framework: str,
    legal_route: str | None,
    acquisition_method: str,
) -> tuple[str, str | None, str]:
    normalized_framework = _validate_controlled_value(
        legal_framework,
        allowed_values=set(LEGAL_FRAMEWORKS),
        field_name="legal_framework",
        required=True,
    )

    normalized_route = _validate_controlled_value(
        legal_route,
        allowed_values=set(LEGAL_ROUTES),
        field_name="legal_route",
    )

    normalized_method = _validate_controlled_value(
        acquisition_method,
        allowed_values=set(ACQUISITION_METHODS),
        field_name="acquisition_method",
        required=True,
    )

    return (
        normalized_framework,
        normalized_route,
        normalized_method,
    )


def _audit_case(
    db: Session,
    *,
    actor_user_id: UUID | None,
    action: str,
    acquisition_case_id: UUID,
    details: dict[str, object] | None = None,
) -> None:
    record_audit_event(
        db,
        actor_user_id=actor_user_id,
        action=action,
        entity_type="acquisition_case",
        entity_id=acquisition_case_id,
        details=details,
        commit=False,
    )


# ---------------------------------------------------------------------------
# List / read
# ---------------------------------------------------------------------------

def list_acquisition_cases(
    db: Session,
    *,
    search: str | None = None,
    status: str | None = None,
    current_stage: str | None = None,
    legal_framework: str | None = None,
    acquisition_method: str | None = None,
    land_requirement_id: UUID | None = None,
    responsible_authority_id: UUID | None = None,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[AcquisitionCase], int]:
    if offset < 0:
        raise ValueError("offset cannot be negative.")

    if limit < 1 or limit > 100:
        raise ValueError("limit must be between 1 and 100.")

    normalized_search = (
        search.strip()
        if search is not None
        else None
    )

    normalized_status = _validate_controlled_value(
        status,
        allowed_values=set(CASE_STATUSES),
        field_name="status",
    )

    normalized_stage = _validate_controlled_value(
        current_stage,
        allowed_values=set(CASE_STAGES),
        field_name="current_stage",
    )

    normalized_framework = _validate_controlled_value(
        legal_framework,
        allowed_values=set(LEGAL_FRAMEWORKS),
        field_name="legal_framework",
    )

    normalized_method = _validate_controlled_value(
        acquisition_method,
        allowed_values=set(ACQUISITION_METHODS),
        field_name="acquisition_method",
    )

    filters: list[Any] = []

    if normalized_search:
        search_pattern = f"%{normalized_search}%"

        filters.append(
            or_(
                AcquisitionCase.case_number.ilike(
                    search_pattern
                ),
                AcquisitionCase.description.ilike(
                    search_pattern
                ),
            )
        )

    if normalized_status:
        filters.append(
            AcquisitionCase.status == normalized_status
        )

    if normalized_stage:
        filters.append(
            AcquisitionCase.current_stage == normalized_stage
        )

    if normalized_framework:
        filters.append(
            AcquisitionCase.legal_framework
            == normalized_framework
        )

    if normalized_method:
        filters.append(
            AcquisitionCase.acquisition_method
            == normalized_method
        )

    if land_requirement_id is not None:
        filters.append(
            AcquisitionCase.land_requirement_id
            == land_requirement_id
        )

    if responsible_authority_id is not None:
        filters.append(
            AcquisitionCase.responsible_authority_id
            == responsible_authority_id
        )

    count_statement = select(
        func.count(AcquisitionCase.id)
    )

    if filters:
        count_statement = count_statement.where(*filters)

    total = db.scalar(count_statement) or 0

    statement = (
        select(AcquisitionCase)
        .order_by(
            AcquisitionCase.created_at.desc(),
            AcquisitionCase.id.desc(),
        )
        .offset(offset)
        .limit(limit)
    )

    if filters:
        statement = statement.where(*filters)

    cases = list(
        db.scalars(statement).all()
    )

    return cases, total


def get_acquisition_case(
    db: Session,
    acquisition_case_id: UUID,
) -> AcquisitionCase:
    return _get_acquisition_case(
        db,
        acquisition_case_id,
    )


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

def create_acquisition_case(
    db: Session,
    *,
    land_requirement_id: UUID,
    case_number: str,
    legal_framework: str = "RFCTLARR_2013",
    legal_route: str | None = None,
    acquisition_method: str = "COMPULSORY_ACQUISITION",
    responsible_authority_id: UUID | None = None,
    assigned_user_id: UUID | None = None,
    description: str | None = None,
    actor_user_id: UUID | None = None,
) -> AcquisitionCase:
    normalized_case_number = _normalize_required_text(
        case_number,
        field_name="case_number",
    )

    normalized_description = _normalize_optional_text(
        description
    )

    (
        normalized_framework,
        normalized_route,
        normalized_method,
    ) = _validate_metadata(
        legal_framework=legal_framework,
        legal_route=legal_route,
        acquisition_method=acquisition_method,
    )

    # Validate parent hierarchy.
    _validate_land_requirement_for_case(
        db,
        land_requirement_id,
    )

    # Validate optional operational assignments.
    _validate_authority(
        db,
        responsible_authority_id,
    )

    _validate_assigned_user(
        db,
        assigned_user_id,
    )

    _ensure_unique_case_number(
        db,
        normalized_case_number,
    )

    acquisition_case = AcquisitionCase(
        land_requirement_id=land_requirement_id,
        case_number=normalized_case_number,
        legal_framework=normalized_framework,
        legal_route=normalized_route,
        acquisition_method=normalized_method,
        responsible_authority_id=responsible_authority_id,
        assigned_user_id=assigned_user_id,
        status=CASE_STATUS_DRAFT,
        current_stage=CASE_STAGE_INITIATION,
        description=normalized_description,
        version=1,
    )

    try:
        db.add(acquisition_case)
        db.flush()

        _audit_case(
            db,
            actor_user_id=actor_user_id,
            action="acquisition_case_created",
            acquisition_case_id=acquisition_case.id,
            details={
                "case_number": acquisition_case.case_number,
                "land_requirement_id": str(
                    acquisition_case.land_requirement_id
                ),
                "legal_framework": acquisition_case.legal_framework,
                "legal_route": acquisition_case.legal_route,
                "acquisition_method": acquisition_case.acquisition_method,
            },
        )

        db.commit()
        db.refresh(acquisition_case)

        return acquisition_case

    except IntegrityError as exc:
        db.rollback()
        raise ValueError(
            "Unable to create Acquisition Case because "
            "a database constraint was violated."
        ) from exc

    except Exception:
        db.rollback()
        raise


# ---------------------------------------------------------------------------
# Update metadata
# ---------------------------------------------------------------------------

def update_acquisition_case(
    db: Session,
    *,
    acquisition_case_id: UUID,
    actor_user_id: UUID | None = None,
    expected_version: int,
    legal_framework: str | None = None,
    legal_route: str | None = None,
    acquisition_method: str | None = None,
    responsible_authority_id: UUID | None = None,
    assigned_user_id: UUID | None = None,
    description: str | None = None,
    update_fields: set[str] | None = None,
) -> AcquisitionCase:
    """
    Update mutable Acquisition Case metadata.

    `update_fields` must contain the fields explicitly supplied by the
    caller. This lets the service distinguish:

        field omitted
        from
        field explicitly set to NULL

    This is important for PATCH semantics.
    """

    _validate_version(expected_version)

    acquisition_case = _get_acquisition_case(
        db,
        acquisition_case_id,
    )

    _validate_case_status(
        acquisition_case,
        allowed_statuses={
            CASE_STATUS_DRAFT,
            CASE_STATUS_ACTIVE,
            CASE_STATUS_ON_HOLD,
        },
        action="update",
    )

    fields = update_fields or set()

    values: dict[str, Any] = {}

    if "legal_framework" in fields:
        if legal_framework is None:
            raise ValueError(
                "legal_framework cannot be null."
            )

        values["legal_framework"] = _validate_controlled_value(
            legal_framework,
            allowed_values=set(LEGAL_FRAMEWORKS),
            field_name="legal_framework",
            required=True,
        )

    if "legal_route" in fields:
        values["legal_route"] = _validate_controlled_value(
            legal_route,
            allowed_values=set(LEGAL_ROUTES),
            field_name="legal_route",
        )

    if "acquisition_method" in fields:
        if acquisition_method is None:
            raise ValueError(
                "acquisition_method cannot be null."
            )

        values["acquisition_method"] = _validate_controlled_value(
            acquisition_method,
            allowed_values=set(ACQUISITION_METHODS),
            field_name="acquisition_method",
            required=True,
        )

    if "responsible_authority_id" in fields:
        _validate_authority(
            db,
            responsible_authority_id,
        )

        values["responsible_authority_id"] = (
            responsible_authority_id
        )

    if "assigned_user_id" in fields:
        _validate_assigned_user(
            db,
            assigned_user_id,
        )

        values["assigned_user_id"] = assigned_user_id

    if "description" in fields:
        values["description"] = _normalize_optional_text(
            description
        )

    if not values:
        raise ValueError(
            "At least one mutable Acquisition Case field "
            "must be provided."
        )

    values["version"] = AcquisitionCase.version + 1

    try:
        result = db.execute(
            update(AcquisitionCase)
            .where(
                AcquisitionCase.id == acquisition_case_id,
                AcquisitionCase.version == expected_version,
            )
            .values(**values)
        )

        if result.rowcount != 1:
            db.rollback()
            raise ValueError(
                "Acquisition Case was modified by another user. "
                "Refresh the case and try again."
            )

        _audit_case(
            db,
            actor_user_id=actor_user_id,
            action="acquisition_case_updated",
            acquisition_case_id=acquisition_case_id,
            details={
                "updated_fields": sorted(values.keys() - {"version"}),
                "previous_version": expected_version,
                "new_version": expected_version + 1,
            },
        )

        db.commit()

        return _get_acquisition_case(
            db,
            acquisition_case_id,
        )

    except ValueError:
        db.rollback()
        raise

    except IntegrityError as exc:
        db.rollback()
        raise ValueError(
            "Unable to update Acquisition Case because "
            "a database constraint was violated."
        ) from exc

    except Exception:
        db.rollback()
        raise


# ---------------------------------------------------------------------------
# Lifecycle commands
# ---------------------------------------------------------------------------

def activate_acquisition_case(
    db: Session,
    *,
    acquisition_case_id: UUID,
    actor_user_id: UUID | None = None,
    expected_version: int,
) -> AcquisitionCase:
    _validate_version(expected_version)

    acquisition_case = _get_acquisition_case(
        db,
        acquisition_case_id,
    )

    if acquisition_case.status != CASE_STATUS_DRAFT:
        raise ValueError(
            "Only draft Acquisition Cases can be activated."
        )

    now = datetime.now(timezone.utc)

    try:
        result = db.execute(
            update(AcquisitionCase)
            .where(
                AcquisitionCase.id == acquisition_case_id,
                AcquisitionCase.status == CASE_STATUS_DRAFT,
                AcquisitionCase.version == expected_version,
            )
            .values(
                status=CASE_STATUS_ACTIVE,
                opened_at=func.coalesce(
                    AcquisitionCase.opened_at,
                    now,
                ),
                version=AcquisitionCase.version + 1,
            )
        )

        if result.rowcount != 1:
            db.rollback()
            raise ValueError(
                "Acquisition Case was modified by another user. "
                "Refresh the case and try again."
            )

        _audit_case(
            db,
            actor_user_id=actor_user_id,
            action="acquisition_case_activated",
            acquisition_case_id=acquisition_case_id,
            details={
                "previous_version": expected_version,
                "new_version": expected_version + 1,
            },
        )

        db.commit()

        return _get_acquisition_case(
            db,
            acquisition_case_id,
        )

    except ValueError:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise


def hold_acquisition_case(
    db: Session,
    *,
    acquisition_case_id: UUID,
    reason: str,
    actor_user_id: UUID | None = None,
    expected_version: int,
) -> AcquisitionCase:
    _validate_version(expected_version)

    normalized_reason = _normalize_required_text(
        reason,
        field_name="reason",
    )

    acquisition_case = _get_acquisition_case(
        db,
        acquisition_case_id,
    )

    if acquisition_case.status != CASE_STATUS_ACTIVE:
        raise ValueError(
            "Only active Acquisition Cases can be put on hold."
        )

    try:
        result = db.execute(
            update(AcquisitionCase)
            .where(
                AcquisitionCase.id == acquisition_case_id,
                AcquisitionCase.status == CASE_STATUS_ACTIVE,
                AcquisitionCase.version == expected_version,
            )
            .values(
                status=CASE_STATUS_ON_HOLD,
                version=AcquisitionCase.version + 1,
            )
        )

        if result.rowcount != 1:
            db.rollback()
            raise ValueError(
                "Acquisition Case was modified by another user. "
                "Refresh the case and try again."
            )

        _audit_case(
            db,
            actor_user_id=actor_user_id,
            action="acquisition_case_put_on_hold",
            acquisition_case_id=acquisition_case_id,
            details={
                "reason": normalized_reason,
                "previous_version": expected_version,
                "new_version": expected_version + 1,
            },
        )

        db.commit()

        return _get_acquisition_case(
            db,
            acquisition_case_id,
        )

    except ValueError:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise


def resume_acquisition_case(
    db: Session,
    *,
    acquisition_case_id: UUID,
    actor_user_id: UUID | None = None,
    expected_version: int,
) -> AcquisitionCase:
    _validate_version(expected_version)

    acquisition_case = _get_acquisition_case(
        db,
        acquisition_case_id,
    )

    if acquisition_case.status != CASE_STATUS_ON_HOLD:
        raise ValueError(
            "Only on-hold Acquisition Cases can be resumed."
        )

    try:
        result = db.execute(
            update(AcquisitionCase)
            .where(
                AcquisitionCase.id == acquisition_case_id,
                AcquisitionCase.status == CASE_STATUS_ON_HOLD,
                AcquisitionCase.version == expected_version,
            )
            .values(
                status=CASE_STATUS_ACTIVE,
                version=AcquisitionCase.version + 1,
            )
        )

        if result.rowcount != 1:
            db.rollback()
            raise ValueError(
                "Acquisition Case was modified by another user. "
                "Refresh the case and try again."
            )

        _audit_case(
            db,
            actor_user_id=actor_user_id,
            action="acquisition_case_resumed",
            acquisition_case_id=acquisition_case_id,
            details={
                "previous_version": expected_version,
                "new_version": expected_version + 1,
            },
        )

        db.commit()

        return _get_acquisition_case(
            db,
            acquisition_case_id,
        )

    except ValueError:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise


def cancel_acquisition_case(
    db: Session,
    *,
    acquisition_case_id: UUID,
    reason: str,
    actor_user_id: UUID | None = None,
    expected_version: int,
) -> AcquisitionCase:
    _validate_version(expected_version)

    normalized_reason = _normalize_required_text(
        reason,
        field_name="reason",
    )

    acquisition_case = _get_acquisition_case(
        db,
        acquisition_case_id,
    )

    if acquisition_case.status in {
        CASE_STATUS_CANCELLED,
        CASE_STATUS_CLOSED,
    }:
        raise ValueError(
            "This Acquisition Case is already in a terminal status."
        )

    if acquisition_case.current_stage in {
        CASE_STAGE_POSSESSION,
        CASE_STAGE_VESTING,
        CASE_STAGE_HANDOVER,
    }:
        raise ValueError(
            "An Acquisition Case cannot be cancelled after "
            "the possession stage has begun."
        )

    try:
        result = db.execute(
            update(AcquisitionCase)
            .where(
                AcquisitionCase.id == acquisition_case_id,
                AcquisitionCase.version == expected_version,
                AcquisitionCase.status.not_in(
                    {
                        CASE_STATUS_CANCELLED,
                        CASE_STATUS_CLOSED,
                    }
                ),
            )
            .values(
                status=CASE_STATUS_CANCELLED,
                closed_at=func.now(),
                version=AcquisitionCase.version + 1,
            )
        )

        if result.rowcount != 1:
            db.rollback()
            raise ValueError(
                "Acquisition Case was modified by another user. "
                "Refresh the case and try again."
            )

        _audit_case(
            db,
            actor_user_id=actor_user_id,
            action="acquisition_case_cancelled",
            acquisition_case_id=acquisition_case_id,
            details={
                "reason": normalized_reason,
                "previous_version": expected_version,
                "new_version": expected_version + 1,
            },
        )

        db.commit()

        return _get_acquisition_case(
            db,
            acquisition_case_id,
        )

    except ValueError:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise


def close_acquisition_case(
    db: Session,
    *,
    acquisition_case_id: UUID,
    actor_user_id: UUID | None = None,
    expected_version: int,
) -> AcquisitionCase:
    _validate_version(expected_version)

    acquisition_case = _get_acquisition_case(
        db,
        acquisition_case_id,
    )

    if acquisition_case.status != CASE_STATUS_ACTIVE:
        raise ValueError(
            "Only active Acquisition Cases can be closed."
        )

    if acquisition_case.current_stage != CASE_STAGE_HANDOVER:
        raise ValueError(
            "Only Acquisition Cases at the HANDOVER stage "
            "can be closed."
        )

    try:
        result = db.execute(
            update(AcquisitionCase)
            .where(
                AcquisitionCase.id == acquisition_case_id,
                AcquisitionCase.status == CASE_STATUS_ACTIVE,
                AcquisitionCase.current_stage == CASE_STAGE_HANDOVER,
                AcquisitionCase.version == expected_version,
            )
            .values(
                status=CASE_STATUS_CLOSED,
                closed_at=func.now(),
                version=AcquisitionCase.version + 1,
            )
        )

        if result.rowcount != 1:
            db.rollback()
            raise ValueError(
                "Acquisition Case was modified by another user. "
                "Refresh the case and try again."
            )

        _audit_case(
            db,
            actor_user_id=actor_user_id,
            action="acquisition_case_closed",
            acquisition_case_id=acquisition_case_id,
            details={
                "previous_version": expected_version,
                "new_version": expected_version + 1,
            },
        )

        db.commit()

        return _get_acquisition_case(
            db,
            acquisition_case_id,
        )

    except ValueError:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise


# ---------------------------------------------------------------------------
# Stage transition
# ---------------------------------------------------------------------------

def transition_acquisition_case_stage(
    db: Session,
    *,
    acquisition_case_id: UUID,
    to_stage: str,
    reason: str | None = None,
    actor_user_id: UUID | None = None,
    expected_version: int,
) -> AcquisitionCase:
    _validate_version(expected_version)

    normalized_stage = _validate_controlled_value(
        to_stage,
        allowed_values=set(CASE_STAGES),
        field_name="to_stage",
        required=True,
    )

    normalized_reason = _normalize_optional_text(
        reason
    )

    acquisition_case = _get_acquisition_case(
        db,
        acquisition_case_id,
    )

    if acquisition_case.status in {
        CASE_STATUS_CANCELLED,
        CASE_STATUS_CLOSED,
    }:
        raise ValueError(
            "Stage transitions are not allowed for terminal "
            "Acquisition Cases."
        )

    if acquisition_case.status == CASE_STATUS_DRAFT:
        raise ValueError(
            "Draft Acquisition Cases must be activated before "
            "their process stage can be advanced."
        )

    if acquisition_case.status == CASE_STATUS_ON_HOLD:
        raise ValueError(
            "On-hold Acquisition Cases must be resumed before "
            "their process stage can be advanced."
        )

    _validate_stage_transition(
        current_stage=acquisition_case.current_stage,
        target_stage=normalized_stage,
    )

    previous_stage = acquisition_case.current_stage

    try:
        result = db.execute(
            update(AcquisitionCase)
            .where(
                AcquisitionCase.id == acquisition_case_id,
                AcquisitionCase.version == expected_version,
                AcquisitionCase.status == CASE_STATUS_ACTIVE,
                AcquisitionCase.current_stage == previous_stage,
            )
            .values(
                current_stage=normalized_stage,
                version=AcquisitionCase.version + 1,
            )
        )

        if result.rowcount != 1:
            db.rollback()
            raise ValueError(
                "Acquisition Case was modified by another user. "
                "Refresh the case and try again."
            )

        history = AcquisitionCaseStageHistory(
            acquisition_case_id=acquisition_case_id,
            from_stage=previous_stage,
            to_stage=normalized_stage,
            reason=normalized_reason,
            changed_by_user_id=actor_user_id,
        )

        db.add(history)

        _audit_case(
            db,
            actor_user_id=actor_user_id,
            action="acquisition_case_stage_changed",
            acquisition_case_id=acquisition_case_id,
            details={
                "from_stage": previous_stage,
                "to_stage": normalized_stage,
                "reason": normalized_reason,
                "previous_version": expected_version,
                "new_version": expected_version + 1,
            },
        )

        db.commit()

        return _get_acquisition_case(
            db,
            acquisition_case_id,
        )

    except ValueError:
        db.rollback()
        raise

    except IntegrityError as exc:
        db.rollback()
        raise ValueError(
            "Unable to transition Acquisition Case because "
            "a database constraint was violated."
        ) from exc

    except Exception:
        db.rollback()
        raise


# ---------------------------------------------------------------------------
# Stage history
# ---------------------------------------------------------------------------

def list_stage_history(
    db: Session,
    *,
    acquisition_case_id: UUID,
) -> list[AcquisitionCaseStageHistory]:
    # Ensure the parent exists before returning an empty history.
    _get_acquisition_case(
        db,
        acquisition_case_id,
    )

    statement = (
        select(AcquisitionCaseStageHistory)
        .where(
            AcquisitionCaseStageHistory.acquisition_case_id
            == acquisition_case_id
        )
        .order_by(
            AcquisitionCaseStageHistory.changed_at.asc(),
            AcquisitionCaseStageHistory.id.asc(),
        )
    )

    return list(
        db.scalars(statement).all()
    )
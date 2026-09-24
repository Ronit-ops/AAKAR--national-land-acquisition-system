from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.land_requirement import LandRequirement
from app.models.project import Project
from app.services.audit_service import record_audit_event


LAND_REQUIREMENT_STATUS_DRAFT = "DRAFT"
LAND_REQUIREMENT_STATUS_SUBMITTED = "SUBMITTED"
LAND_REQUIREMENT_STATUS_UNDER_REVIEW = "UNDER_REVIEW"
LAND_REQUIREMENT_STATUS_APPROVED = "APPROVED"
LAND_REQUIREMENT_STATUS_REJECTED = "REJECTED"
LAND_REQUIREMENT_STATUS_WITHDRAWN = "WITHDRAWN"


LAND_REQUIREMENT_STATUSES = {
    LAND_REQUIREMENT_STATUS_DRAFT,
    LAND_REQUIREMENT_STATUS_SUBMITTED,
    LAND_REQUIREMENT_STATUS_UNDER_REVIEW,
    LAND_REQUIREMENT_STATUS_APPROVED,
    LAND_REQUIREMENT_STATUS_REJECTED,
    LAND_REQUIREMENT_STATUS_WITHDRAWN,
}


def _normalize_text(value: str) -> str:
    return value.strip()


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = value.strip()
    return normalized or None


def _validate_status(status: str) -> None:
    if status not in LAND_REQUIREMENT_STATUSES:
        raise ValueError("Invalid Land Requirement status.")


def _get_project(
    db: Session,
    project_id: UUID,
) -> Project:
    project = db.get(Project, project_id)

    if project is None:
        raise ValueError("Project not found.")

    if project.status == "CLOSED":
        raise ValueError(
            "Cannot create or modify a Land Requirement "
            "for a closed project."
        )

    return project


def _ensure_unique_requirement_reference(
    db: Session,
    *,
    project_id: UUID,
    requirement_reference: str,
    exclude_requirement_id: UUID | None = None,
) -> None:
    statement = select(LandRequirement.id).where(
        LandRequirement.project_id == project_id,
        func.lower(LandRequirement.requirement_reference)
        == requirement_reference.lower(),
    )

    if exclude_requirement_id is not None:
        statement = statement.where(
            LandRequirement.id != exclude_requirement_id,
        )

    existing_requirement_id = db.scalar(statement)

    if existing_requirement_id is not None:
        raise ValueError(
            "A Land Requirement with this reference "
            "already exists for this project."
        )


def _validate_editable_status(
    land_requirement: LandRequirement,
) -> None:
    if land_requirement.status not in {
        LAND_REQUIREMENT_STATUS_DRAFT,
        LAND_REQUIREMENT_STATUS_REJECTED,
    }:
        raise ValueError(
            "Only draft or rejected Land Requirements can be updated."
        )


def list_land_requirements(
    db: Session,
    *,
    search: str | None = None,
    status: str | None = None,
    project_id: UUID | None = None,
    offset: int = 0,
    limit: int = 20,
) -> tuple[list[LandRequirement], int]:
    normalized_search = _normalize_optional_text(search)

    if status is not None:
        status = status.strip().upper()
        _validate_status(status)

    if offset < 0:
        raise ValueError("Offset cannot be negative.")

    if limit < 1 or limit > 100:
        raise ValueError(
            "Limit must be between 1 and 100."
        )

    conditions = []

    if normalized_search:
        search_pattern = f"%{normalized_search}%"

        conditions.append(
            or_(
                LandRequirement.requirement_reference.ilike(
                    search_pattern
                ),
                LandRequirement.purpose.ilike(
                    search_pattern
                ),
                LandRequirement.state.ilike(
                    search_pattern
                ),
                LandRequirement.district.ilike(
                    search_pattern
                ),
                LandRequirement.taluka.ilike(
                    search_pattern
                ),
                LandRequirement.village.ilike(
                    search_pattern
                ),
            )
        )

    if status is not None:
        conditions.append(
            LandRequirement.status == status
        )

    if project_id is not None:
        conditions.append(
            LandRequirement.project_id == project_id
        )

    count_statement = select(
        func.count(LandRequirement.id)
    )

    if conditions:
        count_statement = count_statement.where(
            *conditions
        )

    total = db.scalar(count_statement) or 0

    statement = (
        select(LandRequirement)
        .order_by(
            LandRequirement.created_at.desc(),
            LandRequirement.id.desc(),
        )
        .offset(offset)
        .limit(limit)
    )

    if conditions:
        statement = statement.where(*conditions)

    requirements = list(
        db.scalars(statement).all()
    )

    return requirements, total


def get_land_requirement(
    db: Session,
    land_requirement_id: UUID,
) -> LandRequirement | None:
    return db.get(
        LandRequirement,
        land_requirement_id,
    )


def create_land_requirement(
    db: Session,
    *,
    project_id: UUID,
    requirement_reference: str,
    purpose: str,
    required_area_sq_m: Decimal,
    state: str,
    district: str,
    taluka: str | None,
    village: str | None,
    description: str | None,
    actor_user_id: UUID,
) -> LandRequirement:
    project = _get_project(
        db,
        project_id,
    )

    normalized_reference = _normalize_text(
        requirement_reference
    )
    normalized_purpose = _normalize_text(
        purpose
    )
    normalized_state = _normalize_text(
        state
    )
    normalized_district = _normalize_text(
        district
    )
    normalized_taluka = _normalize_optional_text(
        taluka
    )
    normalized_village = _normalize_optional_text(
        village
    )
    normalized_description = _normalize_optional_text(
        description
    )

    if not normalized_reference:
        raise ValueError(
            "Land Requirement reference cannot be empty."
        )

    if not normalized_purpose:
        raise ValueError(
            "Land Requirement purpose cannot be empty."
        )

    if not normalized_state:
        raise ValueError(
            "Land Requirement state cannot be empty."
        )

    if not normalized_district:
        raise ValueError(
            "Land Requirement district cannot be empty."
        )

    if required_area_sq_m <= 0:
        raise ValueError(
            "Required land area must be greater than zero."
        )

    _ensure_unique_requirement_reference(
        db,
        project_id=project.id,
        requirement_reference=normalized_reference,
    )

    land_requirement = LandRequirement(
        project_id=project.id,
        requirement_reference=normalized_reference,
        purpose=normalized_purpose,
        required_area_sq_m=required_area_sq_m,
        state=normalized_state,
        district=normalized_district,
        taluka=normalized_taluka,
        village=normalized_village,
        description=normalized_description,
        status=LAND_REQUIREMENT_STATUS_DRAFT,
    )

    db.add(land_requirement)

    try:
        db.flush()

        record_audit_event(
            db,
            actor_user_id=actor_user_id,
            action="land_requirement_created",
            entity_type="land_requirement",
            entity_id=land_requirement.id,
            result="success",
            details={
                "project_id": str(
                    land_requirement.project_id
                ),
                "requirement_reference": (
                    land_requirement.requirement_reference
                ),
                "required_area_sq_m": str(
                    land_requirement.required_area_sq_m
                ),
                "status": land_requirement.status,
            },
            commit=False,
        )

        db.commit()
        db.refresh(land_requirement)

        return land_requirement

    except IntegrityError as exc:
        db.rollback()

        raise ValueError(
            "Unable to create the Land Requirement because "
            "it violates a database constraint."
        ) from exc

    except Exception:
        db.rollback()
        raise


def update_land_requirement(
    db: Session,
    *,
    land_requirement_id: UUID,
    requirement_reference: str,
    purpose: str,
    required_area_sq_m: Decimal,
    state: str,
    district: str,
    taluka: str | None,
    village: str | None,
    description: str | None,
    actor_user_id: UUID,
) -> LandRequirement:
    land_requirement = db.get(
        LandRequirement,
        land_requirement_id,
    )

    if land_requirement is None:
        raise ValueError("Land Requirement not found.")

    _validate_editable_status(
        land_requirement
    )

    _get_project(
        db,
        land_requirement.project_id,
    )

    normalized_reference = _normalize_text(
        requirement_reference
    )
    normalized_purpose = _normalize_text(
        purpose
    )
    normalized_state = _normalize_text(
        state
    )
    normalized_district = _normalize_text(
        district
    )
    normalized_taluka = _normalize_optional_text(
        taluka
    )
    normalized_village = _normalize_optional_text(
        village
    )
    normalized_description = _normalize_optional_text(
        description
    )

    if not normalized_reference:
        raise ValueError(
            "Land Requirement reference cannot be empty."
        )

    if not normalized_purpose:
        raise ValueError(
            "Land Requirement purpose cannot be empty."
        )

    if not normalized_state:
        raise ValueError(
            "Land Requirement state cannot be empty."
        )

    if not normalized_district:
        raise ValueError(
            "Land Requirement district cannot be empty."
        )

    if required_area_sq_m <= 0:
        raise ValueError(
            "Required land area must be greater than zero."
        )

    _ensure_unique_requirement_reference(
        db,
        project_id=land_requirement.project_id,
        requirement_reference=normalized_reference,
        exclude_requirement_id=land_requirement.id,
    )

    previous_status = land_requirement.status

    land_requirement.requirement_reference = (
        normalized_reference
    )
    land_requirement.purpose = normalized_purpose
    land_requirement.required_area_sq_m = (
        required_area_sq_m
    )
    land_requirement.state = normalized_state
    land_requirement.district = normalized_district
    land_requirement.taluka = normalized_taluka
    land_requirement.village = normalized_village
    land_requirement.description = normalized_description

    try:
        db.flush()

        record_audit_event(
            db,
            actor_user_id=actor_user_id,
            action="land_requirement_updated",
            entity_type="land_requirement",
            entity_id=land_requirement.id,
            result="success",
            details={
                "requirement_reference": (
                    land_requirement.requirement_reference
                ),
                "previous_status": previous_status,
                "status": land_requirement.status,
            },
            commit=False,
        )

        db.commit()
        db.refresh(land_requirement)

        return land_requirement

    except IntegrityError as exc:
        db.rollback()

        raise ValueError(
            "Unable to update the Land Requirement because "
            "it violates a database constraint."
        ) from exc

    except Exception:
        db.rollback()
        raise


def submit_land_requirement(
    db: Session,
    *,
    land_requirement_id: UUID,
    actor_user_id: UUID,
) -> LandRequirement:
    land_requirement = db.get(
        LandRequirement,
        land_requirement_id,
    )

    if land_requirement is None:
        raise ValueError("Land Requirement not found.")

    if land_requirement.status not in {
        LAND_REQUIREMENT_STATUS_DRAFT,
        LAND_REQUIREMENT_STATUS_REJECTED,
    }:
        raise ValueError(
            "Only draft or rejected Land Requirements "
            "can be submitted."
        )

    previous_status = land_requirement.status

    land_requirement.status = (
        LAND_REQUIREMENT_STATUS_UNDER_REVIEW
    )

    try:
        db.flush()

        record_audit_event(
            db,
            actor_user_id=actor_user_id,
            action="land_requirement_submitted",
            entity_type="land_requirement",
            entity_id=land_requirement.id,
            result="success",
            details={
                "previous_status": previous_status,
                "new_status": land_requirement.status,
            },
            commit=False,
        )

        db.commit()
        db.refresh(land_requirement)

        return land_requirement

    except Exception:
        db.rollback()
        raise


def approve_land_requirement(
    db: Session,
    *,
    land_requirement_id: UUID,
    actor_user_id: UUID,
) -> LandRequirement:
    land_requirement = db.get(
        LandRequirement,
        land_requirement_id,
    )

    if land_requirement is None:
        raise ValueError("Land Requirement not found.")

    if land_requirement.status != (
        LAND_REQUIREMENT_STATUS_UNDER_REVIEW
    ):
        raise ValueError(
            "Only Land Requirements under review "
            "can be approved."
        )

    previous_status = land_requirement.status

    land_requirement.status = (
        LAND_REQUIREMENT_STATUS_APPROVED
    )

    try:
        db.flush()

        record_audit_event(
            db,
            actor_user_id=actor_user_id,
            action="land_requirement_approved",
            entity_type="land_requirement",
            entity_id=land_requirement.id,
            result="success",
            details={
                "previous_status": previous_status,
                "new_status": land_requirement.status,
            },
            commit=False,
        )

        db.commit()
        db.refresh(land_requirement)

        return land_requirement

    except Exception:
        db.rollback()
        raise


def reject_land_requirement(
    db: Session,
    *,
    land_requirement_id: UUID,
    actor_user_id: UUID,
    reason: str | None,
) -> LandRequirement:
    land_requirement = db.get(
        LandRequirement,
        land_requirement_id,
    )

    if land_requirement is None:
        raise ValueError("Land Requirement not found.")

    if land_requirement.status != (
        LAND_REQUIREMENT_STATUS_UNDER_REVIEW
    ):
        raise ValueError(
            "Only Land Requirements under review "
            "can be rejected."
        )

    normalized_reason = _normalize_optional_text(
        reason
    )

    if not normalized_reason:
        raise ValueError(
            "A rejection reason is required."
        )

    previous_status = land_requirement.status

    land_requirement.status = (
        LAND_REQUIREMENT_STATUS_REJECTED
    )

    try:
        db.flush()

        record_audit_event(
            db,
            actor_user_id=actor_user_id,
            action="land_requirement_rejected",
            entity_type="land_requirement",
            entity_id=land_requirement.id,
            result="success",
            details={
                "previous_status": previous_status,
                "new_status": land_requirement.status,
                "reason": normalized_reason,
            },
            commit=False,
        )

        db.commit()
        db.refresh(land_requirement)

        return land_requirement

    except Exception:
        db.rollback()
        raise


def withdraw_land_requirement(
    db: Session,
    *,
    land_requirement_id: UUID,
    actor_user_id: UUID,
    reason: str | None,
) -> LandRequirement:
    land_requirement = db.get(
        LandRequirement,
        land_requirement_id,
    )

    if land_requirement is None:
        raise ValueError("Land Requirement not found.")

    if land_requirement.status not in {
        LAND_REQUIREMENT_STATUS_DRAFT,
        LAND_REQUIREMENT_STATUS_UNDER_REVIEW,
        LAND_REQUIREMENT_STATUS_REJECTED,
    }:
        raise ValueError(
            "This Land Requirement cannot be withdrawn "
            "in its current status."
        )

    normalized_reason = _normalize_optional_text(
        reason
    )

    if not normalized_reason:
        raise ValueError(
            "A withdrawal reason is required."
        )

    previous_status = land_requirement.status

    land_requirement.status = (
        LAND_REQUIREMENT_STATUS_WITHDRAWN
    )

    try:
        db.flush()

        record_audit_event(
            db,
            actor_user_id=actor_user_id,
            action="land_requirement_withdrawn",
            entity_type="land_requirement",
            entity_id=land_requirement.id,
            result="success",
            details={
                "previous_status": previous_status,
                "new_status": land_requirement.status,
                "reason": normalized_reason,
            },
            commit=False,
        )

        db.commit()
        db.refresh(land_requirement)

        return land_requirement

    except Exception:
        db.rollback()
        raise
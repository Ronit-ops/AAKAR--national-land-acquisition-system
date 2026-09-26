from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.parcel import Parcel
from app.services.audit_service import record_audit_event


def _normalize_text(value: str) -> str:
    return value.strip()


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = value.strip()
    return normalized or None


def _ensure_unique_parcel_reference(
    db: Session,
    *,
    parcel_reference: str,
    exclude_parcel_id: UUID | None = None,
) -> None:
    statement = select(Parcel.id).where(
        func.lower(Parcel.parcel_reference)
        == parcel_reference.lower()
    )

    if exclude_parcel_id is not None:
        statement = statement.where(
            Parcel.id != exclude_parcel_id
        )

    existing_id = db.scalar(statement)

    if existing_id is not None:
        raise ValueError(
            "A Parcel with this reference already exists."
        )


def _normalize_parcel_fields(
    *,
    parcel_reference: str,
    state: str,
    district: str,
    taluka: str | None,
    village: str | None,
    survey_number: str,
    subdivision_number: str | None,
    land_category: str | None,
    land_record_reference: str | None,
    source_system: str | None,
) -> dict[str, str | None]:
    normalized = {
        "parcel_reference": _normalize_text(parcel_reference),
        "state": _normalize_text(state),
        "district": _normalize_text(district),
        "taluka": _normalize_optional_text(taluka),
        "village": _normalize_optional_text(village),
        "survey_number": _normalize_text(survey_number),
        "subdivision_number": _normalize_optional_text(
            subdivision_number
        ),
        "land_category": _normalize_optional_text(
            land_category
        ),
        "land_record_reference": _normalize_optional_text(
            land_record_reference
        ),
        "source_system": _normalize_optional_text(
            source_system
        ),
    }

    required_fields = (
        "parcel_reference",
        "state",
        "district",
        "survey_number",
    )

    for field_name in required_fields:
        if not normalized[field_name]:
            raise ValueError(
                f"{field_name.replace('_', ' ').title()} "
                "cannot be empty."
            )

    return normalized


def list_parcels(
    db: Session,
    *,
    search: str | None = None,
    state: str | None = None,
    district: str | None = None,
    taluka: str | None = None,
    village: str | None = None,
    survey_number: str | None = None,
    land_category: str | None = None,
    offset: int = 0,
    limit: int = 20,
) -> tuple[list[Parcel], int]:
    normalized_search = _normalize_optional_text(search)
    normalized_state = _normalize_optional_text(state)
    normalized_district = _normalize_optional_text(district)
    normalized_taluka = _normalize_optional_text(taluka)
    normalized_village = _normalize_optional_text(village)
    normalized_survey_number = _normalize_optional_text(
        survey_number
    )
    normalized_land_category = _normalize_optional_text(
        land_category
    )

    if offset < 0:
        raise ValueError("Offset cannot be negative.")

    if limit < 1 or limit > 100:
        raise ValueError("Limit must be between 1 and 100.")

    conditions = []

    if normalized_search:
        search_pattern = f"%{normalized_search}%"

        conditions.append(
            or_(
                Parcel.parcel_reference.ilike(
                    search_pattern
                ),
                Parcel.survey_number.ilike(
                    search_pattern
                ),
                Parcel.subdivision_number.ilike(
                    search_pattern
                ),
                Parcel.state.ilike(search_pattern),
                Parcel.district.ilike(search_pattern),
                Parcel.taluka.ilike(search_pattern),
                Parcel.village.ilike(search_pattern),
                Parcel.land_record_reference.ilike(
                    search_pattern
                ),
            )
        )

    if normalized_state:
        conditions.append(
            Parcel.state.ilike(normalized_state)
        )

    if normalized_district:
        conditions.append(
            Parcel.district.ilike(normalized_district)
        )

    if normalized_taluka:
        conditions.append(
            Parcel.taluka.ilike(normalized_taluka)
        )

    if normalized_village:
        conditions.append(
            Parcel.village.ilike(normalized_village)
        )

    if normalized_survey_number:
        conditions.append(
            Parcel.survey_number.ilike(
                normalized_survey_number
            )
        )

    if normalized_land_category:
        conditions.append(
            Parcel.land_category.ilike(
                normalized_land_category
            )
        )

    count_statement = select(func.count(Parcel.id))

    if conditions:
        count_statement = count_statement.where(*conditions)

    total = db.scalar(count_statement) or 0

    statement = (
        select(Parcel)
        .order_by(
            Parcel.created_at.desc(),
            Parcel.id.desc(),
        )
        .offset(offset)
        .limit(limit)
    )

    if conditions:
        statement = statement.where(*conditions)

    parcels = list(db.scalars(statement).all())

    return parcels, total


def get_parcel(
    db: Session,
    parcel_id: UUID,
) -> Parcel | None:
    return db.get(Parcel, parcel_id)


def create_parcel(
    db: Session,
    *,
    parcel_reference: str,
    state: str,
    district: str,
    taluka: str | None,
    village: str | None,
    survey_number: str,
    subdivision_number: str | None,
    recorded_area_sq_m: Decimal,
    surveyed_area_sq_m: Decimal | None,
    acquired_area_sq_m: Decimal | None,
    land_category: str | None,
    land_record_reference: str | None,
    source_system: str | None,
    actor_user_id: UUID,
) -> Parcel:
    if recorded_area_sq_m <= 0:
        raise ValueError(
            "Recorded parcel area must be greater than zero."
        )

    if (
        surveyed_area_sq_m is not None
        and surveyed_area_sq_m <= 0
    ):
        raise ValueError(
            "Surveyed parcel area must be greater than zero."
        )

    if (
        acquired_area_sq_m is not None
        and acquired_area_sq_m <= 0
    ):
        raise ValueError(
            "Acquired parcel area must be greater than zero."
        )

    normalized = _normalize_parcel_fields(
        parcel_reference=parcel_reference,
        state=state,
        district=district,
        taluka=taluka,
        village=village,
        survey_number=survey_number,
        subdivision_number=subdivision_number,
        land_category=land_category,
        land_record_reference=land_record_reference,
        source_system=source_system,
    )

    _ensure_unique_parcel_reference(
        db,
        parcel_reference=normalized["parcel_reference"],
    )

    parcel = Parcel(
        parcel_reference=normalized["parcel_reference"],
        state=normalized["state"],
        district=normalized["district"],
        taluka=normalized["taluka"],
        village=normalized["village"],
        survey_number=normalized["survey_number"],
        subdivision_number=normalized["subdivision_number"],
        recorded_area_sq_m=recorded_area_sq_m,
        surveyed_area_sq_m=surveyed_area_sq_m,
        acquired_area_sq_m=acquired_area_sq_m,
        land_category=normalized["land_category"],
        land_record_reference=normalized[
            "land_record_reference"
        ],
        source_system=normalized["source_system"],
    )

    db.add(parcel)

    try:
        db.flush()

        record_audit_event(
            db,
            actor_user_id=actor_user_id,
            action="parcel_created",
            entity_type="parcel",
            entity_id=parcel.id,
            result="success",
            details={
                "parcel_reference": parcel.parcel_reference,
                "state": parcel.state,
                "district": parcel.district,
                "survey_number": parcel.survey_number,
                "recorded_area_sq_m": str(
                    parcel.recorded_area_sq_m
                ),
            },
            commit=False,
        )

        db.commit()
        db.refresh(parcel)

        return parcel

    except IntegrityError as exc:
        db.rollback()

        raise ValueError(
            "Unable to create the Parcel because it "
            "violates a database constraint."
        ) from exc

    except Exception:
        db.rollback()
        raise


def update_parcel(
    db: Session,
    *,
    parcel_id: UUID,
    parcel_reference: str,
    state: str,
    district: str,
    taluka: str | None,
    village: str | None,
    survey_number: str,
    subdivision_number: str | None,
    recorded_area_sq_m: Decimal,
    surveyed_area_sq_m: Decimal | None,
    acquired_area_sq_m: Decimal | None,
    land_category: str | None,
    land_record_reference: str | None,
    source_system: str | None,
    actor_user_id: UUID,
) -> Parcel:
    parcel = db.get(Parcel, parcel_id)

    if parcel is None:
        raise ValueError("Parcel not found.")

    if recorded_area_sq_m <= 0:
        raise ValueError(
            "Recorded parcel area must be greater than zero."
        )

    if (
        surveyed_area_sq_m is not None
        and surveyed_area_sq_m <= 0
    ):
        raise ValueError(
            "Surveyed parcel area must be greater than zero."
        )

    if (
        acquired_area_sq_m is not None
        and acquired_area_sq_m <= 0
    ):
        raise ValueError(
            "Acquired parcel area must be greater than zero."
        )

    normalized = _normalize_parcel_fields(
        parcel_reference=parcel_reference,
        state=state,
        district=district,
        taluka=taluka,
        village=village,
        survey_number=survey_number,
        subdivision_number=subdivision_number,
        land_category=land_category,
        land_record_reference=land_record_reference,
        source_system=source_system,
    )

    _ensure_unique_parcel_reference(
        db,
        parcel_reference=normalized["parcel_reference"],
        exclude_parcel_id=parcel.id,
    )

    previous_values = {
        "parcel_reference": parcel.parcel_reference,
        "state": parcel.state,
        "district": parcel.district,
        "survey_number": parcel.survey_number,
        "recorded_area_sq_m": str(
            parcel.recorded_area_sq_m
        ),
    }

    parcel.parcel_reference = normalized["parcel_reference"]
    parcel.state = normalized["state"]
    parcel.district = normalized["district"]
    parcel.taluka = normalized["taluka"]
    parcel.village = normalized["village"]
    parcel.survey_number = normalized["survey_number"]
    parcel.subdivision_number = normalized[
        "subdivision_number"
    ]
    parcel.recorded_area_sq_m = recorded_area_sq_m
    parcel.surveyed_area_sq_m = surveyed_area_sq_m
    parcel.acquired_area_sq_m = acquired_area_sq_m
    parcel.land_category = normalized["land_category"]
    parcel.land_record_reference = normalized[
        "land_record_reference"
    ]
    parcel.source_system = normalized["source_system"]

    try:
        db.flush()

        record_audit_event(
            db,
            actor_user_id=actor_user_id,
            action="parcel_updated",
            entity_type="parcel",
            entity_id=parcel.id,
            result="success",
            details={
                "previous": previous_values,
                "parcel_reference": parcel.parcel_reference,
                "state": parcel.state,
                "district": parcel.district,
                "survey_number": parcel.survey_number,
                "recorded_area_sq_m": str(
                    parcel.recorded_area_sq_m
                ),
            },
            commit=False,
        )

        db.commit()
        db.refresh(parcel)

        return parcel

    except IntegrityError as exc:
        db.rollback()

        raise ValueError(
            "Unable to update the Parcel because it "
            "violates a database constraint."
        ) from exc

    except Exception:
        db.rollback()
        raise
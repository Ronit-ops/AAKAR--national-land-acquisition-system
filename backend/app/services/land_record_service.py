from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.integrations.land_records.provider import LandRecordProvider
from app.models.land_record_retrieval import LandRecordRetrieval
from app.models.parcel import Parcel
from app.models.parcel_interest import ParcelInterest
from app.models.right_holder import RightHolder
from app.services.audit_service import record_audit_event


def get_parcel_for_land_record_retrieval(
    db: Session,
    parcel_id: UUID,
) -> Parcel | None:
    return db.get(Parcel, parcel_id)


def _get_or_create_right_holder(
    db: Session,
    *,
    source_system: str,
    holder_reference: str,
    holder_type: str,
    display_name: str,
) -> RightHolder:
    statement = select(RightHolder).where(
        RightHolder.source_system == source_system,
        RightHolder.external_reference == holder_reference,
    )

    right_holder = db.scalar(statement)

    if right_holder is not None:
        return right_holder

    right_holder = RightHolder(
        holder_type=holder_type,
        display_name=display_name,
        source_system=source_system,
        external_reference=holder_reference,
        is_active=True,
    )

    db.add(right_holder)

    try:
        with db.begin_nested():
            db.flush()
    except IntegrityError:
        existing = db.scalar(
            select(RightHolder).where(
                RightHolder.source_system == source_system,
                RightHolder.external_reference == holder_reference,
            )
        )

        if existing is None:
            raise

        return existing

    return right_holder


def _upsert_parcel_interest(
    db: Session,
    *,
    parcel_id: UUID,
    right_holder_id: UUID,
    interest_type: str,
    share_percentage,
    provider: str,
    source_record_reference: str | None,
) -> ParcelInterest:
    statement = select(ParcelInterest).where(
        ParcelInterest.parcel_id == parcel_id,
        ParcelInterest.right_holder_id == right_holder_id,
        ParcelInterest.interest_type == interest_type,
    )

    interest = db.scalar(statement)

    if interest is None:
        interest = ParcelInterest(
            parcel_id=parcel_id,
            right_holder_id=right_holder_id,
            interest_type=interest_type,
            share_percentage=share_percentage,
            verification_status="UNVERIFIED",
            record_source=provider,
            record_reference=source_record_reference,
        )

        db.add(interest)
        db.flush()

        return interest

    interest.share_percentage = share_percentage
    interest.record_source = provider
    interest.record_reference = source_record_reference

    db.flush()

    return interest


def retrieve_land_record(
    db: Session,
    *,
    parcel_id: UUID,
    provider: LandRecordProvider,
    actor_user_id: UUID,
) -> LandRecordRetrieval:
    parcel = db.get(Parcel, parcel_id)

    if parcel is None:
        raise ValueError("Parcel not found.")

    requested_at = datetime.now(timezone.utc)

    try:
        result = provider.retrieve(
            parcel_id=parcel.id,
            state=parcel.state,
            district=parcel.district,
            taluka=parcel.taluka,
            village=parcel.village,
            survey_number=parcel.survey_number,
            subdivision_number=parcel.subdivision_number,
        )

    except Exception as exc:
        retrieval = LandRecordRetrieval(
            parcel_id=parcel.id,
            provider=provider.provider_name,
            source_system="UNKNOWN",
            requested_at=requested_at,
            retrieved_at=datetime.now(timezone.utc),
            status="FAILED",
            error_code="PROVIDER_ERROR",
            error_message=str(exc)[:4000],
        )

        db.add(retrieval)

        record_audit_event(
            db,
            actor_user_id=actor_user_id,
            action="land_record_retrieval_failed",
            entity_type="parcel",
            entity_id=parcel.id,
            result="failure",
            details={
                "provider": provider.provider_name,
                "error_code": "PROVIDER_ERROR",
            },
            commit=False,
        )

        db.commit()
        db.refresh(retrieval)

        raise ValueError(
            "Unable to retrieve the land record from the provider."
        ) from exc

    retrieval_status = "SUCCESS" if result.found else "NO_RECORD"

    retrieval = LandRecordRetrieval(
        parcel_id=parcel.id,
        provider=result.provider,
        source_system=result.source_system,
        source_record_reference=result.source_record_reference,
        requested_at=requested_at,
        retrieved_at=result.retrieved_at,
        status=retrieval_status,
        source_version=result.source_version,
    )

    db.add(retrieval)
    db.flush()

    if result.found:
        for holder in result.holders:
            right_holder = _get_or_create_right_holder(
                db,
                source_system=result.source_system,
                holder_reference=holder.holder_reference,
                holder_type=holder.holder_type,
                display_name=holder.display_name,
            )

            _upsert_parcel_interest(
                db,
                parcel_id=parcel.id,
                right_holder_id=right_holder.id,
                interest_type=holder.interest_type,
                share_percentage=holder.share_percentage,
                provider=result.provider,
                source_record_reference=result.source_record_reference,
            )

    record_audit_event(
        db,
        actor_user_id=actor_user_id,
        action="land_record_retrieved",
        entity_type="parcel",
        entity_id=parcel.id,
        result="success",
        details={
            "provider": result.provider,
            "source_system": result.source_system,
            "source_record_reference": result.source_record_reference,
            "status": retrieval_status,
            "holder_count": len(result.holders),
        },
        commit=False,
    )

    try:
        db.commit()
        db.refresh(retrieval)

        return retrieval

    except IntegrityError as exc:
        db.rollback()

        raise ValueError(
            "Unable to save the retrieved land-record information "
            "because it conflicts with existing data."
        ) from exc

    except Exception:
        db.rollback()
        raise
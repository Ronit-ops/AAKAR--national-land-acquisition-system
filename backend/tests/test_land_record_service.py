from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.integrations.land_records.mock_provider import (
    MockLandRecordProvider,
)
from app.models.audit_event import AuditEvent
from app.models.land_record_retrieval import LandRecordRetrieval
from app.models.parcel import Parcel
from app.models.parcel_interest import ParcelInterest
from app.models.right_holder import RightHolder
from app.models.user import User
from app.services.land_record_service import retrieve_land_record
from app.services.parcel_service import create_parcel


def create_test_user(db):
    user = User(
        id=uuid4(),
        email=f"land-record-{uuid4().hex[:10]}@example.com",
        password_hash=hash_password("TestPassword123!"),
        full_name="Land Record Test User",
        is_active=True,
    )

    db.add(user)
    db.flush()

    return user


def create_test_parcel(db, *, user_id):
    return create_parcel(
        db,
        parcel_reference=f"PAR-LR-{uuid4().hex[:10].upper()}",
        state="Maharashtra",
        district="Pune",
        taluka="Haveli",
        village="Wagholi",
        survey_number=f"{uuid4().hex[:6]}/1",
        subdivision_number="1",
        recorded_area_sq_m=Decimal("2500.0000"),
        surveyed_area_sq_m=None,
        acquired_area_sq_m=None,
        land_category="AGRICULTURAL",
        land_record_reference="7/12-TEST",
        source_system="TEST",
        actor_user_id=user_id,
    )


def cleanup_test_data(
    db,
    *,
    parcel_id=None,
    user_id=None,
):
    try:
        right_holder_ids = []

        if parcel_id is not None:
            right_holder_ids = [
                row[0]
                for row in db.execute(
                    select(ParcelInterest.right_holder_id).where(
                        ParcelInterest.parcel_id == parcel_id
                    )
                ).all()
            ]

            db.query(ParcelInterest).filter(
                ParcelInterest.parcel_id == parcel_id
            ).delete(
                synchronize_session=False
            )

            db.query(LandRecordRetrieval).filter(
                LandRecordRetrieval.parcel_id == parcel_id
            ).delete(
                synchronize_session=False
            )

            db.query(AuditEvent).filter(
                AuditEvent.entity_id == parcel_id
            ).delete(
                synchronize_session=False
            )

            db.query(Parcel).filter(
                Parcel.id == parcel_id
            ).delete(
                synchronize_session=False
            )

        if right_holder_ids:
            db.query(RightHolder).filter(
                RightHolder.id.in_(right_holder_ids)
            ).delete(
                synchronize_session=False
            )

        if user_id is not None:
            db.query(AuditEvent).filter(
                AuditEvent.actor_user_id == user_id
            ).delete(
                synchronize_session=False
            )

            db.query(User).filter(
                User.id == user_id
            ).delete(
                synchronize_session=False
            )

        db.commit()

    except Exception:
        db.rollback()
        raise


def test_successful_land_record_retrieval():
    db = SessionLocal()
    user = create_test_user(db)
    parcel = None

    try:
        parcel = create_test_parcel(
            db,
            user_id=user.id,
        )

        retrieval = retrieve_land_record(
            db,
            parcel_id=parcel.id,
            provider=MockLandRecordProvider(),
            actor_user_id=user.id,
        )

        assert retrieval.status == "SUCCESS"
        assert retrieval.provider == "MOCK_LAND_RECORDS"
        assert retrieval.source_system == "MOCK_LAND_RECORD_SYSTEM"
        assert retrieval.source_record_reference is not None

        interests = db.execute(
            select(ParcelInterest).where(
                ParcelInterest.parcel_id == parcel.id
            )
        ).scalars().all()

        assert len(interests) == 1

        right_holder = db.get(
            RightHolder,
            interests[0].right_holder_id,
        )

        assert right_holder is not None
        assert right_holder.source_system == (
            "MOCK_LAND_RECORD_SYSTEM"
        )
        assert right_holder.external_reference.startswith(
            "MOCK-HOLDER-"
        )
        assert right_holder.display_name.startswith(
            "Recorded Holder - "
        )

        assert interests[0].interest_type == "OWNER"
        assert interests[0].share_percentage == Decimal(
            "100.00000"
        )
        assert interests[0].verification_status == "UNVERIFIED"

        audit = db.execute(
            select(AuditEvent).where(
                AuditEvent.entity_id == parcel.id,
                AuditEvent.action == "land_record_retrieved",
            )
        ).scalars().all()

        assert audit

    finally:
        cleanup_test_data(
            db,
            parcel_id=parcel.id if parcel else None,
            user_id=user.id,
        )
        db.close()


def test_repeated_retrieval_reuses_existing_holder_and_interest():
    db = SessionLocal()
    user = create_test_user(db)
    parcel = None

    try:
        parcel = create_test_parcel(
            db,
            user_id=user.id,
        )

        provider = MockLandRecordProvider()

        first = retrieve_land_record(
            db,
            parcel_id=parcel.id,
            provider=provider,
            actor_user_id=user.id,
        )

        second = retrieve_land_record(
            db,
            parcel_id=parcel.id,
            provider=provider,
            actor_user_id=user.id,
        )

        assert first.id != second.id

        interests = db.execute(
            select(ParcelInterest).where(
                ParcelInterest.parcel_id == parcel.id
            )
        ).scalars().all()

        assert len(interests) == 1

        right_holder = db.get(
            RightHolder,
            interests[0].right_holder_id,
        )

        assert right_holder is not None
        assert right_holder.source_system == (
            "MOCK_LAND_RECORD_SYSTEM"
        )

        retrievals = db.execute(
            select(LandRecordRetrieval).where(
                LandRecordRetrieval.parcel_id == parcel.id
            )
        ).scalars().all()

        assert len(retrievals) == 2

    finally:
        cleanup_test_data(
            db,
            parcel_id=parcel.id if parcel else None,
            user_id=user.id,
        )
        db.close()


def test_missing_parcel_is_rejected():
    db = SessionLocal()
    user = create_test_user(db)

    try:
        with pytest.raises(
            ValueError,
            match="Parcel not found",
        ):
            retrieve_land_record(
                db,
                parcel_id=uuid4(),
                provider=MockLandRecordProvider(),
                actor_user_id=user.id,
            )

    finally:
        cleanup_test_data(
            db,
            user_id=user.id,
        )
        db.close()


def test_provider_failure_is_recorded():
    class FailingProvider(MockLandRecordProvider):
        @property
        def provider_name(self) -> str:
            return "FAILING_TEST_PROVIDER"

        def retrieve(self, **kwargs):
            raise RuntimeError("Test provider failure")

    db = SessionLocal()
    user = create_test_user(db)
    parcel = None

    try:
        parcel = create_test_parcel(
            db,
            user_id=user.id,
        )

        with pytest.raises(
            ValueError,
            match="Unable to retrieve the land record",
        ):
            retrieve_land_record(
                db,
                parcel_id=parcel.id,
                provider=FailingProvider(),
                actor_user_id=user.id,
            )

        failures = db.execute(
            select(LandRecordRetrieval).where(
                LandRecordRetrieval.parcel_id == parcel.id,
                LandRecordRetrieval.status == "FAILED",
            )
        ).scalars().all()

        assert len(failures) == 1
        assert failures[0].provider == "FAILING_TEST_PROVIDER"
        assert failures[0].error_code == "PROVIDER_ERROR"

        interests = db.execute(
            select(ParcelInterest).where(
                ParcelInterest.parcel_id == parcel.id
            )
        ).scalars().all()

        assert interests == []

    finally:
        cleanup_test_data(
            db,
            parcel_id=parcel.id if parcel else None,
            user_id=user.id,
        )
        db.close()
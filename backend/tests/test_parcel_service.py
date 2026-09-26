from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.audit_event import AuditEvent
from app.models.parcel import Parcel
from app.models.user import User
from app.services.parcel_service import (
    create_parcel,
    get_parcel,
    list_parcels,
    update_parcel,
)


def create_test_user(db):
    user = User(
        id=uuid4(),
        email=f"parcel-{uuid4().hex[:10]}@example.com",
        password_hash=hash_password("TestPassword123!"),
        full_name="Parcel Test User",
        is_active=True,
    )

    db.add(user)
    db.flush()

    return user


def create_test_parcel(
    db,
    *,
    user_id,
    parcel_reference=None,
    survey_number="123/1",
):
    return create_parcel(
        db,
        parcel_reference=(
            parcel_reference
            or f"PAR-{uuid4().hex[:10].upper()}"
        ),
        state="Maharashtra",
        district="Pune",
        taluka="Haveli",
        village="Wagholi",
        survey_number=survey_number,
        subdivision_number="1",
        recorded_area_sq_m=Decimal("2500.0000"),
        surveyed_area_sq_m=None,
        acquired_area_sq_m=None,
        land_category="AGRICULTURAL",
        land_record_reference="7/12-TEST",
        source_system="TEST",
        actor_user_id=user_id,
    )


def cleanup_parcel_tree(
    db,
    *,
    parcel_ids=None,
    user_id=None,
):
    try:
        if parcel_ids:
            db.query(AuditEvent).filter(
                AuditEvent.entity_id.in_(parcel_ids)
            ).delete(
                synchronize_session=False
            )

            db.query(Parcel).filter(
                Parcel.id.in_(parcel_ids)
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


def test_create_parcel():
    db = SessionLocal()
    user = create_test_user(db)
    parcel = None

    try:
        parcel = create_test_parcel(
            db,
            user_id=user.id,
        )

        assert parcel.id is not None
        assert parcel.parcel_reference.startswith("PAR-")
        assert parcel.state == "Maharashtra"
        assert parcel.district == "Pune"
        assert parcel.survey_number == "123/1"
        assert parcel.recorded_area_sq_m == Decimal(
            "2500.0000"
        )

        audit = db.execute(
            select(AuditEvent).where(
                AuditEvent.entity_id == parcel.id
            )
        ).scalars().all()

        assert audit
        assert audit[0].action == "parcel_created"

    finally:
        cleanup_parcel_tree(
            db,
            parcel_ids=[parcel.id] if parcel else None,
            user_id=user.id,
        )
        db.close()


def test_duplicate_parcel_reference_is_rejected():
    db = SessionLocal()
    user = create_test_user(db)
    parcel = None

    parcel_reference = (
        f"PAR-DUP-{uuid4().hex[:8].upper()}"
    )

    try:
        parcel = create_test_parcel(
            db,
            user_id=user.id,
            parcel_reference=parcel_reference,
        )

        with pytest.raises(
            ValueError,
            match="already exists",
        ):
            create_test_parcel(
                db,
                user_id=user.id,
                parcel_reference=parcel_reference,
            )

    finally:
        cleanup_parcel_tree(
            db,
            parcel_ids=[parcel.id] if parcel else None,
            user_id=user.id,
        )
        db.close()


def test_get_parcel():
    db = SessionLocal()
    user = create_test_user(db)
    parcel = None

    try:
        parcel = create_test_parcel(
            db,
            user_id=user.id,
        )

        fetched = get_parcel(
            db,
            parcel.id,
        )

        assert fetched is not None
        assert fetched.id == parcel.id
        assert (
            fetched.parcel_reference
            == parcel.parcel_reference
        )

    finally:
        cleanup_parcel_tree(
            db,
            parcel_ids=[parcel.id] if parcel else None,
            user_id=user.id,
        )
        db.close()


def test_list_parcels_supports_search_and_filters():
    db = SessionLocal()
    user = create_test_user(db)
    first = None
    second = None

    try:
        first = create_test_parcel(
            db,
            user_id=user.id,
            parcel_reference=(
                f"PAR-PUNE-{uuid4().hex[:8].upper()}"
            ),
            survey_number="100/1",
        )

        second = create_test_parcel(
            db,
            user_id=user.id,
            parcel_reference=(
                f"PAR-PUNE-{uuid4().hex[:8].upper()}"
            ),
            survey_number="200/1",
        )

        parcels, total = list_parcels(
            db,
            search="100/1",
        )

        ids = {parcel.id for parcel in parcels}

        assert first.id in ids
        assert second.id not in ids
        assert total >= 1

        parcels, total = list_parcels(
            db,
            state="maharashtra",
            district="pune",
            village="wagholi",
        )

        ids = {parcel.id for parcel in parcels}

        assert first.id in ids
        assert second.id in ids
        assert total >= 2

    finally:
        cleanup_parcel_tree(
            db,
            parcel_ids=[
                parcel.id
                for parcel in (first, second)
                if parcel is not None
            ],
            user_id=user.id,
        )
        db.close()


def test_update_parcel():
    db = SessionLocal()
    user = create_test_user(db)
    parcel = None

    try:
        parcel = create_test_parcel(
            db,
            user_id=user.id,
        )

        updated = update_parcel(
            db,
            parcel_id=parcel.id,
            parcel_reference=parcel.parcel_reference,
            state="Maharashtra",
            district="Pune",
            taluka="Mulshi",
            village="Pirangut",
            survey_number="999/2",
            subdivision_number="2",
            recorded_area_sq_m=Decimal("3000.0000"),
            surveyed_area_sq_m=Decimal("2990.0000"),
            acquired_area_sq_m=None,
            land_category="RESIDENTIAL",
            land_record_reference="7/12-UPDATED",
            source_system="SURVEY_SYSTEM",
            actor_user_id=user.id,
        )

        assert updated.id == parcel.id
        assert updated.taluka == "Mulshi"
        assert updated.village == "Pirangut"
        assert updated.survey_number == "999/2"
        assert updated.recorded_area_sq_m == Decimal(
            "3000.0000"
        )
        assert updated.surveyed_area_sq_m == Decimal(
            "2990.0000"
        )

        audit = db.execute(
            select(AuditEvent).where(
                AuditEvent.entity_id == parcel.id,
                AuditEvent.action == "parcel_updated",
            )
        ).scalars().all()

        assert audit

    finally:
        cleanup_parcel_tree(
            db,
            parcel_ids=[parcel.id] if parcel else None,
            user_id=user.id,
        )
        db.close()


def test_update_nonexistent_parcel_is_rejected():
    db = SessionLocal()
    user = create_test_user(db)

    try:
        with pytest.raises(
            ValueError,
            match="Parcel not found",
        ):
            update_parcel(
                db,
                parcel_id=uuid4(),
                parcel_reference="PAR-MISSING",
                state="Maharashtra",
                district="Pune",
                taluka="Haveli",
                village="Wagholi",
                survey_number="1/1",
                subdivision_number=None,
                recorded_area_sq_m=Decimal(
                    "1000.0000"
                ),
                surveyed_area_sq_m=None,
                acquired_area_sq_m=None,
                land_category=None,
                land_record_reference=None,
                source_system=None,
                actor_user_id=user.id,
            )

    finally:
        cleanup_parcel_tree(
            db,
            user_id=user.id,
        )
        db.close()


def test_invalid_parcel_area_is_rejected():
    db = SessionLocal()
    user = create_test_user(db)

    try:
        with pytest.raises(
            ValueError,
            match="Recorded parcel area",
        ):
            create_parcel(
                db,
                parcel_reference=(
                    f"PAR-INVALID-{uuid4().hex[:8]}"
                ),
                state="Maharashtra",
                district="Pune",
                taluka="Haveli",
                village="Wagholi",
                survey_number="500/1",
                subdivision_number=None,
                recorded_area_sq_m=Decimal("0"),
                surveyed_area_sq_m=None,
                acquired_area_sq_m=None,
                land_category=None,
                land_record_reference=None,
                source_system=None,
                actor_user_id=user.id,
            )

    finally:
        cleanup_parcel_tree(
            db,
            user_id=user.id,
        )
        db.close()
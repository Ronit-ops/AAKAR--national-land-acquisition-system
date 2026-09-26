from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.core.jwt import create_access_token
from app.db.session import SessionLocal
from app.main import app
from app.models.audit_event import AuditEvent
from app.models.land_record_retrieval import LandRecordRetrieval
from app.models.parcel import Parcel
from app.models.parcel_interest import ParcelInterest
from app.models.right_holder import RightHolder
from app.models.user import User
from app.services.auth_service import create_user
from app.services.rbac_service import assign_role


client = TestClient(app)

TEST_PASSWORD = "AAKAR-Land-Record-API-123!"
PARCEL_PATH = "/api/v1/parcels"


def create_test_user(
    *,
    full_name: str,
) -> User:
    db = SessionLocal()

    try:
        return create_user(
            db=db,
            email=f"land-record-api-{uuid4()}@example.com",
            password=TEST_PASSWORD,
            full_name=full_name,
        )
    finally:
        db.close()


def assign_test_role(
    *,
    user_id,
    role_code: str,
) -> None:
    db = SessionLocal()

    try:
        assign_role(
            db=db,
            user_id=user_id,
            role_code=role_code,
        )
    finally:
        db.close()


def auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(user.id)

    return {
        "Authorization": f"Bearer {token}",
    }


def parcel_payload(
    *,
    parcel_reference: str | None = None,
    survey_number: str | None = None,
) -> dict:
    survey_number = (
        survey_number
        or f"LR-{uuid4().hex[:8].upper()}"
    )

    return {
        "parcel_reference": (
            parcel_reference
            or f"PAR-LR-API-{uuid4().hex[:8].upper()}"
        ),
        "state": "Maharashtra",
        "district": "Pune",
        "taluka": "Haveli",
        "village": "Wagholi",
        "survey_number": survey_number,
        "subdivision_number": "1",
        "recorded_area_sq_m": 2500,
        "surveyed_area_sq_m": None,
        "acquired_area_sq_m": None,
        "land_category": "AGRICULTURAL",
        "land_record_reference": "7/12-LR-API-TEST",
        "source_system": "API_TEST",
    }


def delete_parcel(
    parcel_id,
) -> None:
    db = SessionLocal()

    try:
        right_holder_ids = [
            row[0]
            for row in db.query(
                ParcelInterest.right_holder_id
            )
            .filter(
                ParcelInterest.parcel_id == parcel_id,
            )
            .all()
        ]

        db.execute(
            delete(AuditEvent).where(
                AuditEvent.entity_type == "parcel",
                AuditEvent.entity_id == parcel_id,
            )
        )

        db.execute(
            delete(LandRecordRetrieval).where(
                LandRecordRetrieval.parcel_id == parcel_id,
            )
        )

        db.execute(
            delete(ParcelInterest).where(
                ParcelInterest.parcel_id == parcel_id,
            )
        )

        parcel = db.get(
            Parcel,
            parcel_id,
        )

        if parcel is not None:
            db.delete(parcel)

        db.flush()

        for right_holder_id in right_holder_ids:
            right_holder = db.get(
                RightHolder,
                right_holder_id,
            )

            if right_holder is None:
                continue

            remaining_interest = (
                db.query(ParcelInterest)
                .filter(
                    ParcelInterest.right_holder_id
                    == right_holder_id,
                )
                .first()
            )

            if remaining_interest is None:
                db.delete(right_holder)

        db.commit()

    finally:
        db.close()


def delete_user(
    user_id,
) -> None:
    db = SessionLocal()

    try:
        db.execute(
            delete(AuditEvent).where(
                AuditEvent.actor_user_id == user_id,
            )
        )

        user = db.get(
            User,
            user_id,
        )

        if user is not None:
            db.delete(user)

        db.commit()

    finally:
        db.close()


def test_land_record_retrieval_requires_authentication():
    response = client.post(
        f"{PARCEL_PATH}/{uuid4()}/land-record/retrieve",
    )

    assert response.status_code == 401


def test_land_record_retrieval_requires_permission():
    user = create_test_user(
        full_name="Land Record API Unauthorized User",
    )

    try:
        response = client.post(
            f"{PARCEL_PATH}/{uuid4()}/land-record/retrieve",
            headers=auth_headers(user),
        )

        assert response.status_code == 403

    finally:
        delete_user(user.id)


def test_land_record_retrieval_not_found_returns_404():
    user = create_test_user(
        full_name="Land Record API Not Found User",
    )

    assign_test_role(
        user_id=user.id,
        role_code="land_acquisition_officer",
    )

    try:
        response = client.post(
            f"{PARCEL_PATH}/{uuid4()}/land-record/retrieve",
            headers=auth_headers(user),
        )

        assert response.status_code == 404
        assert response.json()["detail"] == (
            "Parcel not found."
        )

    finally:
        delete_user(user.id)


def test_land_record_retrieval_success():
    user = create_test_user(
        full_name="Land Record API Retrieval User",
    )

    assign_test_role(
        user_id=user.id,
        role_code="land_acquisition_officer",
    )

    parcel_id = None

    try:
        create_response = client.post(
            PARCEL_PATH,
            json=parcel_payload(
                parcel_reference="PAR-LR-SUCCESS-001",
                survey_number="LR-SUCCESS-001",
            ),
            headers=auth_headers(user),
        )

        assert create_response.status_code == 201

        parcel_id = create_response.json()["id"]

        response = client.post(
            f"{PARCEL_PATH}/{parcel_id}/land-record/retrieve",
            headers=auth_headers(user),
        )

        assert response.status_code == 200

        body = response.json()

        assert body["parcel_id"] == parcel_id
        assert body["provider"] == "MOCK_LAND_RECORDS"
        assert body["source_system"] == (
            "MOCK_LAND_RECORD_SYSTEM"
        )
        assert body["source_record_reference"] == (
            "MOCK-Maharashtra-Pune-LR-SUCCESS-001"
        )
        assert body["status"] == "SUCCESS"
        assert body["source_version"] == "MOCK-1.0"
        assert body["error_code"] is None

        db = SessionLocal()

        try:
            retrieval = (
                db.query(LandRecordRetrieval)
                .filter(
                    LandRecordRetrieval.parcel_id
                    == parcel_id,
                )
                .one()
            )

            assert retrieval.status == "SUCCESS"
            assert retrieval.provider == (
                "MOCK_LAND_RECORDS"
            )

            interests = (
                db.query(ParcelInterest)
                .filter(
                    ParcelInterest.parcel_id
                    == parcel_id,
                )
                .all()
            )

            assert len(interests) == 1

            interest = interests[0]

            assert interest.interest_type == "OWNER"
            assert interest.share_percentage == 100
            assert interest.verification_status == (
                "UNVERIFIED"
            )
            assert interest.record_source == (
                "MOCK_LAND_RECORDS"
            )
            assert interest.record_reference == (
                "MOCK-Maharashtra-Pune-LR-SUCCESS-001"
            )

            right_holder = db.get(
                RightHolder,
                interest.right_holder_id,
            )

            assert right_holder is not None
            assert right_holder.display_name == (
                "Recorded Holder - LR-SUCCESS-001"
            )
            assert right_holder.holder_type == "INDIVIDUAL"
            assert right_holder.source_system == (
                "MOCK_LAND_RECORD_SYSTEM"
            )
            assert right_holder.external_reference == (
                "MOCK-HOLDER-LR-SUCCESS-001"
            )

            audit_events = (
                db.query(AuditEvent)
                .filter(
                    AuditEvent.entity_type == "parcel",
                    AuditEvent.entity_id == parcel_id,
                    AuditEvent.action
                    == "land_record_retrieved",
                )
                .all()
            )

            assert len(audit_events) == 1
            assert audit_events[0].result == "success"

        finally:
            db.close()

    finally:
        if parcel_id is not None:
            delete_parcel(parcel_id)

        delete_user(user.id)


def test_repeated_land_record_retrieval_does_not_duplicate_interest():
    user = create_test_user(
        full_name="Land Record API Repeat User",
    )

    assign_test_role(
        user_id=user.id,
        role_code="land_acquisition_officer",
    )

    parcel_id = None

    try:
        create_response = client.post(
            PARCEL_PATH,
            json=parcel_payload(
                parcel_reference="PAR-LR-REPEAT-001",
                survey_number="LR-REPEAT-001",
            ),
            headers=auth_headers(user),
        )

        assert create_response.status_code == 201

        parcel_id = create_response.json()["id"]

        first_response = client.post(
            f"{PARCEL_PATH}/{parcel_id}/land-record/retrieve",
            headers=auth_headers(user),
        )

        assert first_response.status_code == 200

        second_response = client.post(
            f"{PARCEL_PATH}/{parcel_id}/land-record/retrieve",
            headers=auth_headers(user),
        )

        assert second_response.status_code == 200

        db = SessionLocal()

        try:
            retrievals = (
                db.query(LandRecordRetrieval)
                .filter(
                    LandRecordRetrieval.parcel_id
                    == parcel_id,
                )
                .all()
            )

            assert len(retrievals) == 2

            interests = (
                db.query(ParcelInterest)
                .filter(
                    ParcelInterest.parcel_id
                    == parcel_id,
                )
                .all()
            )

            assert len(interests) == 1

            right_holders = (
                db.query(RightHolder)
                .filter(
                    RightHolder.source_system
                    == "MOCK_LAND_RECORD_SYSTEM",
                    RightHolder.external_reference
                    == "MOCK-HOLDER-LR-REPEAT-001",
                )
                .all()
            )

            assert len(right_holders) == 1

        finally:
            db.close()

    finally:
        if parcel_id is not None:
            delete_parcel(parcel_id)

        delete_user(user.id)


def test_land_record_retrieval_records_audit_event():
    user = create_test_user(
        full_name="Land Record API Audit User",
    )

    assign_test_role(
        user_id=user.id,
        role_code="land_acquisition_officer",
    )

    parcel_id = None

    try:
        create_response = client.post(
            PARCEL_PATH,
            json=parcel_payload(
                parcel_reference="PAR-LR-AUDIT-001",
                survey_number="LR-AUDIT-001",
            ),
            headers=auth_headers(user),
        )

        assert create_response.status_code == 201

        parcel_id = create_response.json()["id"]

        response = client.post(
            f"{PARCEL_PATH}/{parcel_id}/land-record/retrieve",
            headers=auth_headers(user),
        )

        assert response.status_code == 200

        db = SessionLocal()

        try:
            events = (
                db.query(AuditEvent)
                .filter(
                    AuditEvent.entity_type == "parcel",
                    AuditEvent.entity_id == parcel_id,
                    AuditEvent.actor_user_id == user.id,
                )
                .all()
            )

            actions = {
                event.action
                for event in events
            }

            assert "parcel_created" in actions
            assert "land_record_retrieved" in actions

        finally:
            db.close()

    finally:
        if parcel_id is not None:
            delete_parcel(parcel_id)

        delete_user(user.id)


def test_land_record_retrieval_provider_failure():
    user = create_test_user(
        full_name="Land Record API Provider Failure User",
    )

    assign_test_role(
        user_id=user.id,
        role_code="land_acquisition_officer",
    )

    parcel_id = None

    try:
        create_response = client.post(
            PARCEL_PATH,
            json=parcel_payload(
                parcel_reference="PAR-LR-FAILURE-001",
                survey_number="LR-FAILURE-001",
            ),
            headers=auth_headers(user),
        )

        assert create_response.status_code == 201

        parcel_id = create_response.json()["id"]

        with patch(
            "app.api.v1.endpoints.parcels"
            ".get_land_record_provider"
        ) as provider_factory:
            provider = provider_factory.return_value
            provider.provider_name = "FAILING_PROVIDER"

            provider.retrieve.side_effect = RuntimeError(
                "Simulated provider failure"
            )

            response = client.post(
                f"{PARCEL_PATH}/{parcel_id}"
                "/land-record/retrieve",
                headers=auth_headers(user),
            )

        assert response.status_code == 409
        assert response.json()["detail"] == (
            "Unable to retrieve the land record "
            "from the provider."
        )

        db = SessionLocal()

        try:
            retrieval = (
                db.query(LandRecordRetrieval)
                .filter(
                    LandRecordRetrieval.parcel_id
                    == parcel_id,
                )
                .one()
            )

            assert retrieval.status == "FAILED"
            assert retrieval.provider == (
                "FAILING_PROVIDER"
            )
            assert retrieval.source_system == "UNKNOWN"
            assert retrieval.error_code == "PROVIDER_ERROR"
            assert retrieval.error_message == (
                "Simulated provider failure"
            )

            audit_events = (
                db.query(AuditEvent)
                .filter(
                    AuditEvent.entity_type == "parcel",
                    AuditEvent.entity_id == parcel_id,
                    AuditEvent.action
                    == "land_record_retrieval_failed",
                )
                .all()
            )

            assert len(audit_events) == 1
            assert audit_events[0].result == "failure"

        finally:
            db.close()

    finally:
        if parcel_id is not None:
            delete_parcel(parcel_id)

        delete_user(user.id)
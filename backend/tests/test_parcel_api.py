from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.core.jwt import create_access_token
from app.db.session import SessionLocal
from app.main import app
from app.models.audit_event import AuditEvent
from app.models.parcel import Parcel
from app.models.user import User
from app.services.auth_service import create_user
from app.services.rbac_service import assign_role


client = TestClient(app)

TEST_PASSWORD = "AAKAR-Parcel-API-123!"
PARCEL_PATH = "/api/v1/parcels"


def create_test_user(
    *,
    full_name: str,
) -> User:
    db = SessionLocal()

    try:
        return create_user(
            db=db,
            email=f"parcel-api-{uuid4()}@example.com",
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
    survey_number: str = "123/1",
) -> dict:
    return {
        "parcel_reference": (
            parcel_reference
            or f"PAR-API-{uuid4().hex[:8].upper()}"
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
        "land_record_reference": "7/12-API-TEST",
        "source_system": "API_TEST",
    }


def delete_parcel(parcel_id) -> None:
    db = SessionLocal()

    try:
        db.execute(
            delete(AuditEvent).where(
                AuditEvent.entity_type == "parcel",
                AuditEvent.entity_id == parcel_id,
            )
        )

        parcel = db.get(
            Parcel,
            parcel_id,
        )

        if parcel is not None:
            db.delete(parcel)

        db.commit()

    finally:
        db.close()


def delete_user(user_id) -> None:
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


def test_parcel_list_requires_authentication():
    response = client.get(PARCEL_PATH)

    assert response.status_code == 401


def test_parcel_create_requires_permission():
    user = create_test_user(
        full_name="Parcel API Unauthorized User",
    )

    try:
        response = client.post(
            PARCEL_PATH,
            json=parcel_payload(),
            headers=auth_headers(user),
        )

        assert response.status_code == 403

    finally:
        delete_user(user.id)


def test_parcel_create_get_and_list():
    user = create_test_user(
        full_name="Parcel API Administrator",
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
                parcel_reference="PAR-API-CRUD-001",
            ),
            headers=auth_headers(user),
        )

        assert create_response.status_code == 201

        parcel = create_response.json()

        parcel_id = parcel["id"]

        assert parcel["parcel_reference"] == (
            "PAR-API-CRUD-001"
        )
        assert parcel["state"] == "Maharashtra"
        assert parcel["district"] == "Pune"
        assert parcel["survey_number"] == "123/1"
        assert parcel["recorded_area_sq_m"] == "2500.0000"
        assert parcel["surveyed_area_sq_m"] is None
        assert parcel["acquired_area_sq_m"] is None
        assert parcel["geometry"] is None

        get_response = client.get(
            f"{PARCEL_PATH}/{parcel_id}",
            headers=auth_headers(user),
        )

        assert get_response.status_code == 200

        get_body = get_response.json()

        assert get_body["id"] == parcel_id
        assert get_body["parcel_reference"] == (
            "PAR-API-CRUD-001"
        )

        list_response = client.get(
            PARCEL_PATH,
            params={
                "survey_number": "123/1",
            },
            headers=auth_headers(user),
        )

        assert list_response.status_code == 200

        list_body = list_response.json()

        assert "items" in list_body
        assert "total" in list_body
        assert "offset" in list_body
        assert "limit" in list_body

        assert any(
            item["id"] == parcel_id
            for item in list_body["items"]
        )

    finally:
        if parcel_id is not None:
            delete_parcel(parcel_id)

        delete_user(user.id)


def test_parcel_search():
    user = create_test_user(
        full_name="Parcel API Search User",
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
                parcel_reference="PAR-SEARCH-UNIQUE",
                survey_number="987/5",
            ),
            headers=auth_headers(user),
        )

        assert create_response.status_code == 201

        parcel_id = create_response.json()["id"]

        response = client.get(
            PARCEL_PATH,
            params={
                "search": "PAR-SEARCH-UNIQUE",
            },
            headers=auth_headers(user),
        )

        assert response.status_code == 200

        body = response.json()

        assert body["total"] >= 1

        assert any(
            item["id"] == parcel_id
            for item in body["items"]
        )

    finally:
        if parcel_id is not None:
            delete_parcel(parcel_id)

        delete_user(user.id)


def test_parcel_update():
    user = create_test_user(
        full_name="Parcel API Update User",
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
                parcel_reference="PAR-UPDATE-001",
            ),
            headers=auth_headers(user),
        )

        assert create_response.status_code == 201

        created = create_response.json()
        parcel_id = created["id"]

        update_response = client.put(
            f"{PARCEL_PATH}/{parcel_id}",
            json={
                "parcel_reference": (
                    "PAR-UPDATE-001"
                ),
                "state": "Maharashtra",
                "district": "Pune",
                "taluka": "Mulshi",
                "village": "Pirangut",
                "survey_number": "999/2",
                "subdivision_number": "2",
                "recorded_area_sq_m": 3000,
                "surveyed_area_sq_m": 2990,
                "acquired_area_sq_m": None,
                "land_category": "RESIDENTIAL",
                "land_record_reference": (
                    "7/12-UPDATED"
                ),
                "source_system": "SURVEY_SYSTEM",
            },
            headers=auth_headers(user),
        )

        assert update_response.status_code == 200

        body = update_response.json()

        assert body["id"] == parcel_id
        assert body["taluka"] == "Mulshi"
        assert body["village"] == "Pirangut"
        assert body["survey_number"] == "999/2"
        assert body["recorded_area_sq_m"] == (
            "3000.0000"
        )
        assert body["surveyed_area_sq_m"] == (
            "2990.0000"
        )
        assert body["land_category"] == "RESIDENTIAL"

    finally:
        if parcel_id is not None:
            delete_parcel(parcel_id)

        delete_user(user.id)


def test_parcel_update_requires_permission():
    creator = create_test_user(
        full_name="Parcel API Creator",
    )

    assign_test_role(
        user_id=creator.id,
        role_code="land_acquisition_officer",
    )

    unauthorized = create_test_user(
        full_name="Parcel API Unauthorized Updater",
    )

    parcel_id = None

    try:
        create_response = client.post(
            PARCEL_PATH,
            json=parcel_payload(
                parcel_reference="PAR-UPDATE-AUTH-001",
            ),
            headers=auth_headers(creator),
        )

        assert create_response.status_code == 201

        parcel_id = create_response.json()["id"]

        response = client.put(
            f"{PARCEL_PATH}/{parcel_id}",
            json=parcel_payload(
                parcel_reference="PAR-UPDATE-AUTH-001",
            ),
            headers=auth_headers(unauthorized),
        )

        assert response.status_code == 403

    finally:
        if parcel_id is not None:
            delete_parcel(parcel_id)

        delete_user(creator.id)
        delete_user(unauthorized.id)


def test_parcel_not_found_returns_404():
    user = create_test_user(
        full_name="Parcel API Not Found User",
    )

    assign_test_role(
        user_id=user.id,
        role_code="land_acquisition_officer",
    )

    try:
        response = client.get(
            f"{PARCEL_PATH}/{uuid4()}",
            headers=auth_headers(user),
        )

        assert response.status_code == 404
        assert response.json()["detail"] == (
            "Parcel not found."
        )

    finally:
        delete_user(user.id)


def test_parcel_duplicate_reference_returns_409():
    user = create_test_user(
        full_name="Parcel API Duplicate User",
    )

    assign_test_role(
        user_id=user.id,
        role_code="land_acquisition_officer",
    )

    parcel_id = None

    try:
        first_response = client.post(
            PARCEL_PATH,
            json=parcel_payload(
                parcel_reference="PAR-DUPLICATE-001",
            ),
            headers=auth_headers(user),
        )

        assert first_response.status_code == 201

        parcel_id = first_response.json()["id"]

        second_response = client.post(
            PARCEL_PATH,
            json=parcel_payload(
                parcel_reference="PAR-DUPLICATE-001",
            ),
            headers=auth_headers(user),
        )

        assert second_response.status_code == 409

        assert "already exists" in (
            second_response.json()["detail"]
        )

    finally:
        if parcel_id is not None:
            delete_parcel(parcel_id)

        delete_user(user.id)


def test_parcel_validation_returns_422():
    user = create_test_user(
        full_name="Parcel API Validation User",
    )

    assign_test_role(
        user_id=user.id,
        role_code="land_acquisition_officer",
    )

    try:
        response = client.post(
            PARCEL_PATH,
            json={
                "parcel_reference": "",
                "state": "Maharashtra",
                "district": "Pune",
                "taluka": "Haveli",
                "village": "Wagholi",
                "survey_number": "1/1",
                "subdivision_number": None,
                "recorded_area_sq_m": -100,
                "surveyed_area_sq_m": None,
                "acquired_area_sq_m": None,
                "land_category": None,
                "land_record_reference": None,
                "source_system": None,
            },
            headers=auth_headers(user),
        )

        assert response.status_code == 422

    finally:
        delete_user(user.id)


def test_parcel_audit_event_is_recorded():
    user = create_test_user(
        full_name="Parcel API Audit User",
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
                parcel_reference="PAR-AUDIT-001",
            ),
            headers=auth_headers(user),
        )

        assert create_response.status_code == 201

        parcel_id = create_response.json()["id"]

        db = SessionLocal()

        try:
            actions = {
                row.action
                for row in db.query(AuditEvent)
                .filter(
                    AuditEvent.entity_type == "parcel",
                    AuditEvent.entity_id == parcel_id,
                )
                .all()
            }

        finally:
            db.close()

        assert "parcel_created" in actions

    finally:
        if parcel_id is not None:
            delete_parcel(parcel_id)

        delete_user(user.id)
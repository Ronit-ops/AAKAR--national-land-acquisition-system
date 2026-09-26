from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.jwt import create_access_token
from app.db.session import SessionLocal
from app.main import app
from app.models.user import User
from app.services.auth_service import create_user
from app.services.rbac_service import assign_role


client = TestClient(app)

TEST_PASSWORD = "AAKAR-RBAC-API-123!"


def create_api_test_user() -> User:
    db = SessionLocal()

    try:
        return create_user(
            db=db,
            email=f"rbac-api-{uuid4()}@example.com",
            password=TEST_PASSWORD,
            full_name="RBAC API Test User",
        )
    finally:
        db.close()


def delete_api_test_user(user_id) -> None:
    db = SessionLocal()

    try:
        user = db.get(User, user_id)

        if user is not None:
            db.delete(user)
            db.commit()
    finally:
        db.close()


def auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(user.id)
    return {
        "Authorization": f"Bearer {token}",
    }


def test_my_roles_requires_authentication():
    response = client.get("/api/v1/rbac/me")

    assert response.status_code == 401


def test_my_roles_returns_empty_roles_for_new_user():
    user = create_api_test_user()

    try:
        response = client.get(
            "/api/v1/rbac/me",
            headers=auth_headers(user),
        )

        assert response.status_code == 200

        body = response.json()

        assert body["user_id"] == str(user.id)
        assert body["roles"] == []
    finally:
        delete_api_test_user(user.id)


def test_my_roles_returns_assigned_roles():
    user = create_api_test_user()

    db = SessionLocal()

    try:
        assign_role(
            db=db,
            user_id=user.id,
            role_code="district_collector",
        )

        assign_role(
            db=db,
            user_id=user.id,
            role_code="survey_gis_officer",
        )
    finally:
        db.close()

    try:
        response = client.get(
            "/api/v1/rbac/me",
            headers=auth_headers(user),
        )

        assert response.status_code == 200

        role_codes = {
            role["code"]
            for role in response.json()["roles"]
        }

        assert role_codes == {
            "district_collector",
            "survey_gis_officer",
        }
    finally:
        delete_api_test_user(user.id)


def test_role_catalog_requires_authentication():
    response = client.get("/api/v1/rbac/roles")

    assert response.status_code == 401


def test_role_catalog_returns_active_roles():
    user = create_api_test_user()

    try:
        response = client.get(
            "/api/v1/rbac/roles",
            headers=auth_headers(user),
        )

        assert response.status_code == 200

        roles = response.json()

        role_codes = {
            role["code"]
            for role in roles
        }

        expected_role_codes = {
            "aakar_development_admin",
            "additional_collector",
            "affected_family",
            "audit_compliance",
            "authorized_representative",
            "central_ministry_officer",
            "district_collector",
            "field_verification_officer",
            "infrastructure_officer",
            "land_acquisition_officer",
            "landowner_recorded_right_holder",
            "national_administrator",
            "national_monitoring_officer",
            "project_director",
            "revenue_officer",
            "rr_officer",
            "state_department_officer",
            "state_land_authority_officer",
            "state_nodal_officer",
            "survey_gis_officer",
            "system_administrator",
        }

        assert role_codes == expected_role_codes
    finally:
        delete_api_test_user(user.id)


def test_role_assignment_requires_system_administrator():
    user = create_api_test_user()
    target = create_api_test_user()

    try:
        response = client.post(
            f"/api/v1/rbac/users/{target.id}/roles",
            headers=auth_headers(user),
            json={"role_code": "district_collector"},
        )

        assert response.status_code == 403
    finally:
        delete_api_test_user(user.id)
        delete_api_test_user(target.id)


def test_system_administrator_can_assign_role():
    admin = create_api_test_user()
    target = create_api_test_user()

    db = SessionLocal()

    try:
        assign_role(
            db=db,
            user_id=admin.id,
            role_code="system_administrator",
        )
    finally:
        db.close()

    try:
        response = client.post(
            f"/api/v1/rbac/users/{target.id}/roles",
            headers=auth_headers(admin),
            json={"role_code": "district_collector"},
        )

        assert response.status_code == 201

        body = response.json()

        assert body["user_id"] == str(target.id)
        assert body["role"]["code"] == "district_collector"
    finally:
        delete_api_test_user(admin.id)
        delete_api_test_user(target.id)


def test_assigning_unknown_role_returns_404():
    admin = create_api_test_user()
    target = create_api_test_user()

    db = SessionLocal()

    try:
        assign_role(
            db=db,
            user_id=admin.id,
            role_code="system_administrator",
        )
    finally:
        db.close()

    try:
        response = client.post(
            f"/api/v1/rbac/users/{target.id}/roles",
            headers=auth_headers(admin),
            json={"role_code": "does_not_exist"},
        )

        assert response.status_code == 404
    finally:
        delete_api_test_user(admin.id)
        delete_api_test_user(target.id)


def test_system_administrator_can_remove_role():
    admin = create_api_test_user()
    target = create_api_test_user()

    db = SessionLocal()

    try:
        assign_role(
            db=db,
            user_id=admin.id,
            role_code="system_administrator",
        )

        assign_role(
            db=db,
            user_id=target.id,
            role_code="district_collector",
        )
    finally:
        db.close()

    try:
        response = client.delete(
            f"/api/v1/rbac/users/{target.id}/roles/district_collector",
            headers=auth_headers(admin),
        )

        assert response.status_code == 204
    finally:
        delete_api_test_user(admin.id)
        delete_api_test_user(target.id)


def test_remove_missing_role_returns_404():
    admin = create_api_test_user()
    target = create_api_test_user()

    db = SessionLocal()

    try:
        assign_role(
            db=db,
            user_id=admin.id,
            role_code="system_administrator",
        )
    finally:
        db.close()

    try:
        response = client.delete(
            f"/api/v1/rbac/users/{target.id}/roles/district_collector",
            headers=auth_headers(admin),
        )

        assert response.status_code == 404
    finally:
        delete_api_test_user(admin.id)
        delete_api_test_user(target.id)

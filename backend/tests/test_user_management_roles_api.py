from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.jwt import create_access_token
from app.db.session import SessionLocal
from app.main import app
from app.models.user import User
from app.services.auth_service import create_user
from app.services.rbac_service import assign_role


client = TestClient(app)

TEST_PASSWORD = "AAKAR-User-Roles-API-123!"


def create_test_user(
    *,
    full_name: str,
) -> User:
    db = SessionLocal()

    try:
        return create_user(
            db=db,
            email=f"user-role-detail-{uuid4()}@example.com",
            password=TEST_PASSWORD,
            full_name=full_name,
        )
    finally:
        db.close()


def create_admin() -> User:
    user = create_test_user(
        full_name="User Management Administrator",
    )

    db = SessionLocal()

    try:
        assign_role(
            db=db,
            user_id=user.id,
            role_code="system_administrator",
        )
    finally:
        db.close()

    return user


def delete_test_user(user_id) -> None:
    db = SessionLocal()

    try:
        user = db.get(User, user_id)

        if user is not None:
            db.delete(user)
            db.commit()
    finally:
        db.close()


def auth_headers(user: User) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {create_access_token(user.id)}",
    }


def test_user_details_require_authentication():
    target = create_test_user(
        full_name="Protected User",
    )

    try:
        response = client.get(
            f"/api/v1/users/{target.id}",
        )

        assert response.status_code == 401
    finally:
        delete_test_user(target.id)


def test_user_details_forbid_non_administrator():
    user = create_test_user(
        full_name="Regular User",
    )
    target = create_test_user(
        full_name="Protected User",
    )

    try:
        response = client.get(
            f"/api/v1/users/{target.id}",
            headers=auth_headers(user),
        )

        assert response.status_code == 403
    finally:
        delete_test_user(user.id)
        delete_test_user(target.id)


def test_user_details_include_assigned_roles():
    admin = create_admin()
    target = create_test_user(
        full_name="Role Detail Target",
    )

    db = SessionLocal()

    try:
        assign_role(
            db=db,
            user_id=target.id,
            role_code="district_collector",
        )

        assign_role(
            db=db,
            user_id=target.id,
            role_code="survey_gis_officer",
        )
    finally:
        db.close()

    try:
        response = client.get(
            f"/api/v1/users/{target.id}",
            headers=auth_headers(admin),
        )

        assert response.status_code == 200

        body = response.json()

        assert body["id"] == str(target.id)
        assert body["full_name"] == "Role Detail Target"

        role_codes = {
            role["code"]
            for role in body["roles"]
        }

        assert role_codes == {
            "district_collector",
            "survey_gis_officer",
        }
    finally:
        delete_test_user(admin.id)
        delete_test_user(target.id)


def test_user_details_do_not_expose_password_hash():
    admin = create_admin()
    target = create_test_user(
        full_name="Sensitive Data Target",
    )

    try:
        response = client.get(
            f"/api/v1/users/{target.id}",
            headers=auth_headers(admin),
        )

        assert response.status_code == 200
        assert "password_hash" not in response.json()
    finally:
        delete_test_user(admin.id)
        delete_test_user(target.id)


def test_unknown_user_still_returns_404():
    admin = create_admin()

    try:
        response = client.get(
            f"/api/v1/users/{uuid4()}",
            headers=auth_headers(admin),
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "User not found."
    finally:
        delete_test_user(admin.id)
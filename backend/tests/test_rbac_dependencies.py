from typing import Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.deps import require_any_role, require_role
from app.core.jwt import create_access_token
from app.db.session import SessionLocal
from app.models.user import User
from app.services.auth_service import create_user
from app.services.rbac_service import assign_role, remove_role


TEST_EMAIL_PREFIX = "rbac-dependency-test"
TEST_PASSWORD = "AAKAR-RBAC-Dependency-123!"


def create_test_user() -> User:
    db = SessionLocal()

    try:
        user = create_user(
            db=db,
            email=f"{TEST_EMAIL_PREFIX}-{uuid4()}@example.com",
            password=TEST_PASSWORD,
            full_name="RBAC Dependency Test User",
        )

        return user
    finally:
        db.close()


def delete_test_user(user_id) -> None:
    db = SessionLocal()

    try:
        user = db.get(User, user_id)

        if user is not None:
            db.delete(user)
            db.commit()
    finally:
        db.close()


app = FastAPI()


@app.get("/test/role")
def role_endpoint(
    current_user: Annotated[
        User,
        Depends(require_role("district_collector")),
    ],
):
    return {
        "user_id": str(current_user.id),
        "authorized": True,
    }


@app.get("/test/any-role")
def any_role_endpoint(
    current_user: Annotated[
        User,
        Depends(
            require_any_role(
                "district_collector",
                "additional_collector",
            )
        ),
    ],
):
    return {
        "user_id": str(current_user.id),
        "authorized": True,
    }


client = TestClient(app)


def login_and_get_token(user: User) -> str:
    return create_access_token(user.id)


def test_missing_token_returns_401():
    response = client.get("/test/role")

    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials."


def test_user_without_required_role_gets_403():
    user = create_test_user()

    try:
        token = login_and_get_token(user)

        response = client.get(
            "/test/role",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403
        assert (
            response.json()["detail"]
            == "You do not have permission to access this resource."
        )
    finally:
        delete_test_user(user.id)


def test_user_with_required_role_gets_200():
    user = create_test_user()

    db = SessionLocal()

    try:
        assign_role(
            db=db,
            user_id=user.id,
            role_code="district_collector",
        )
    finally:
        db.close()

    try:
        token = login_and_get_token(user)

        response = client.get(
            "/test/role",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json()["authorized"] is True
        assert response.json()["user_id"] == str(user.id)
    finally:
        delete_test_user(user.id)


def test_role_matching_is_case_insensitive():
    user = create_test_user()

    db = SessionLocal()

    try:
        assign_role(
            db=db,
            user_id=user.id,
            role_code="DISTRICT_COLLECTOR",
        )
    finally:
        db.close()

    try:
        token = login_and_get_token(user)

        response = client.get(
            "/test/role",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
    finally:
        delete_test_user(user.id)


def test_any_role_allows_first_matching_role():
    user = create_test_user()

    db = SessionLocal()

    try:
        assign_role(
            db=db,
            user_id=user.id,
            role_code="additional_collector",
        )
    finally:
        db.close()

    try:
        token = login_and_get_token(user)

        response = client.get(
            "/test/any-role",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json()["authorized"] is True
    finally:
        delete_test_user(user.id)


def test_any_role_returns_403_when_no_role_matches():
    user = create_test_user()

    try:
        token = login_and_get_token(user)

        response = client.get(
            "/test/any-role",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403
    finally:
        delete_test_user(user.id)


def test_role_change_takes_effect_without_new_token():
    user = create_test_user()

    db = SessionLocal()

    try:
        token = login_and_get_token(user)

        first_response = client.get(
            "/test/role",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert first_response.status_code == 403

        assign_role(
            db=db,
            user_id=user.id,
            role_code="district_collector",
        )

        second_response = client.get(
            "/test/role",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert second_response.status_code == 200
    finally:
        db.close()
        delete_test_user(user.id)


def test_removed_role_is_immediately_denied():
    user = create_test_user()

    db = SessionLocal()

    try:
        assign_role(
            db=db,
            user_id=user.id,
            role_code="district_collector",
        )

        token = login_and_get_token(user)

        authorized_response = client.get(
            "/test/role",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert authorized_response.status_code == 200

        removed = remove_role(
            db=db,
            user_id=user.id,
            role_code="district_collector",
        )

        assert removed is True

        denied_response = client.get(
            "/test/role",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert denied_response.status_code == 403
    finally:
        db.close()
        delete_test_user(user.id)
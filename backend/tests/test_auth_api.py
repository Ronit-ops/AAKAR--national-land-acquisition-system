from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.core.jwt import decode_access_token
from app.db.session import SessionLocal
from app.main import app
from app.models.user import User
from app.services.auth_service import create_user


client = TestClient(app)

TEST_EMAIL = "auth-api-test@example.com"
TEST_PASSWORD = "AAKAR-Test-Password-123!"
TEST_NAME = "API Test User"


def cleanup_test_user() -> None:
    """Remove the API test user from the database."""
    db = SessionLocal()

    try:
        db.execute(
            delete(User).where(User.email == TEST_EMAIL)
        )
        db.commit()
    finally:
        db.close()


def test_register_user():
    cleanup_test_user()

    try:
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD,
                "full_name": TEST_NAME,
            },
        )

        assert response.status_code == 201

        data = response.json()

        assert data["email"] == TEST_EMAIL
        assert data["full_name"] == TEST_NAME
        assert data["is_active"] is True
        assert data["is_email_verified"] is False
        assert "password_hash" not in data
        assert "password" not in data
    finally:
        cleanup_test_user()


def test_register_duplicate_email():
    cleanup_test_user()

    try:
        payload = {
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
            "full_name": TEST_NAME,
        }

        first_response = client.post(
            "/api/v1/auth/register",
            json=payload,
        )

        assert first_response.status_code == 201

        second_response = client.post(
            "/api/v1/auth/register",
            json=payload,
        )

        assert second_response.status_code == 409
        assert second_response.json()["detail"] == (
            "A user with this email already exists."
        )
    finally:
        cleanup_test_user()


def test_register_invalid_email():
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "not-an-email",
            "password": TEST_PASSWORD,
            "full_name": TEST_NAME,
        },
    )

    assert response.status_code == 422


def test_register_short_password():
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": TEST_EMAIL,
            "password": "short",
            "full_name": TEST_NAME,
        },
    )

    assert response.status_code == 422


def test_login_success():
    cleanup_test_user()

    try:
        client.post(
            "/api/v1/auth/register",
            json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD,
                "full_name": TEST_NAME,
            },
        )

        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD,
            },
        )

        assert response.status_code == 200

        data = response.json()

        assert data["access_token"]
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == 1800

        assert data["user"]["email"] == TEST_EMAIL
        assert data["user"]["full_name"] == TEST_NAME
        assert data["user"]["is_active"] is True
        assert data["user"]["is_email_verified"] is False

        assert "password" not in data
        assert "password_hash" not in data

        payload = decode_access_token(data["access_token"])

        assert payload["sub"] == data["user"]["id"]
        assert "iat" in payload
        assert "exp" in payload
    finally:
        cleanup_test_user()


def test_login_normalizes_email():
    cleanup_test_user()

    try:
        client.post(
            "/api/v1/auth/register",
            json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD,
                "full_name": TEST_NAME,
            },
        )

        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "AUTH-API-TEST@EXAMPLE.COM",
                "password": TEST_PASSWORD,
            },
        )

        assert response.status_code == 200
        assert response.json()["user"]["email"] == TEST_EMAIL
    finally:
        cleanup_test_user()


def test_login_updates_last_login_at():
    cleanup_test_user()

    try:
        client.post(
            "/api/v1/auth/register",
            json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD,
                "full_name": TEST_NAME,
            },
        )

        db = SessionLocal()

        try:
            user = db.query(User).filter(
                User.email == TEST_EMAIL
            ).first()

            assert user is not None
            assert user.last_login_at is None
        finally:
            db.close()

        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD,
            },
        )

        assert response.status_code == 200

        db = SessionLocal()

        try:
            user = db.query(User).filter(
                User.email == TEST_EMAIL
            ).first()

            assert user is not None
            assert user.last_login_at is not None
        finally:
            db.close()
    finally:
        cleanup_test_user()


def test_login_wrong_password():
    cleanup_test_user()

    try:
        client.post(
            "/api/v1/auth/register",
            json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD,
                "full_name": TEST_NAME,
            },
        )

        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": TEST_EMAIL,
                "password": "Wrong-Password!",
            },
        )

        assert response.status_code == 401
        assert response.json()["detail"] == "Incorrect email or password."
        assert response.headers["www-authenticate"] == "Bearer"
    finally:
        cleanup_test_user()


def test_login_unknown_email():
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "unknown-user@example.com",
            "password": TEST_PASSWORD,
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password."


def test_login_inactive_user():
    cleanup_test_user()

    db = SessionLocal()

    try:
        user = create_user(
            db=db,
            email=TEST_EMAIL,
            password=TEST_PASSWORD,
            full_name=TEST_NAME,
        )

        user.is_active = False
        db.commit()
    finally:
        db.close()

    try:
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD,
            },
        )

        assert response.status_code == 401
        assert response.json()["detail"] == "Incorrect email or password."
    finally:
        cleanup_test_user()


def test_login_invalid_email():
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "not-an-email",
            "password": TEST_PASSWORD,
        },
    )

    assert response.status_code == 422


def test_login_empty_password():
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": TEST_EMAIL,
            "password": "",
        },
    )

    assert response.status_code == 422
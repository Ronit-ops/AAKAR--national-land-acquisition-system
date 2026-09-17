from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db.session import SessionLocal
from app.main import app
from app.models.user import User


client = TestClient(app)

TEST_EMAIL = "auth-api-test@example.com"


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
                "password": "AAKAR-Test-Password-123!",
                "full_name": "API Test User",
            },
        )

        assert response.status_code == 201

        data = response.json()

        assert data["email"] == TEST_EMAIL
        assert data["full_name"] == "API Test User"
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
            "password": "AAKAR-Test-Password-123!",
            "full_name": "API Test User",
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
            "password": "AAKAR-Test-Password-123!",
            "full_name": "API Test User",
        },
    )

    assert response.status_code == 422


def test_register_short_password():
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": TEST_EMAIL,
            "password": "short",
            "full_name": "API Test User",
        },
    )

    assert response.status_code == 422
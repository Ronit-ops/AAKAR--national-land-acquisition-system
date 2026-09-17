from sqlalchemy import delete

from app.db.session import SessionLocal
from app.models.user import User
from app.services.auth_service import (
    authenticate_user,
    create_user,
    get_user_by_email,
)


TEST_EMAIL = "auth-service-test@aakar.local"
TEST_PASSWORD = "AAKAR-Test-Password-123!"
TEST_NAME = "Authentication Service Test User"


def cleanup_test_user() -> None:
    """Remove the authentication test user from the database."""
    db = SessionLocal()

    try:
        db.execute(
            delete(User).where(User.email == TEST_EMAIL)
        )
        db.commit()
    finally:
        db.close()


def test_create_user():
    cleanup_test_user()

    db = SessionLocal()

    try:
        user = create_user(
            db=db,
            email=TEST_EMAIL,
            password=TEST_PASSWORD,
            full_name=TEST_NAME,
        )

        assert user.email == TEST_EMAIL
        assert user.full_name == TEST_NAME
        assert user.is_active is True
        assert user.is_email_verified is False
        assert user.password_hash.startswith("$argon2")
        assert user.password_hash != TEST_PASSWORD
    finally:
        db.close()
        cleanup_test_user()


def test_get_user_by_email_normalizes_email():
    cleanup_test_user()

    db = SessionLocal()

    try:
        create_user(
            db=db,
            email=TEST_EMAIL,
            password=TEST_PASSWORD,
            full_name=TEST_NAME,
        )

        user = get_user_by_email(
            db,
            "  AUTH-SERVICE-TEST@AAKAR.LOCAL  ",
        )

        assert user is not None
        assert user.email == TEST_EMAIL
    finally:
        db.close()
        cleanup_test_user()


def test_authenticate_user_with_correct_password():
    cleanup_test_user()

    db = SessionLocal()

    try:
        create_user(
            db=db,
            email=TEST_EMAIL,
            password=TEST_PASSWORD,
            full_name=TEST_NAME,
        )

        user = authenticate_user(
            db=db,
            email=TEST_EMAIL,
            password=TEST_PASSWORD,
        )

        assert user is not None
        assert user.email == TEST_EMAIL
    finally:
        db.close()
        cleanup_test_user()


def test_authenticate_user_rejects_wrong_password():
    cleanup_test_user()

    db = SessionLocal()

    try:
        create_user(
            db=db,
            email=TEST_EMAIL,
            password=TEST_PASSWORD,
            full_name=TEST_NAME,
        )

        user = authenticate_user(
            db=db,
            email=TEST_EMAIL,
            password="Wrong-Password!",
        )

        assert user is None
    finally:
        db.close()
        cleanup_test_user()


def test_authenticate_user_rejects_inactive_user():
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

        authenticated_user = authenticate_user(
            db=db,
            email=TEST_EMAIL,
            password=TEST_PASSWORD,
        )

        assert authenticated_user is None
    finally:
        db.close()
        cleanup_test_user()
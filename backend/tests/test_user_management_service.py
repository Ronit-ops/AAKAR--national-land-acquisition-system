from uuid import uuid4

import pytest

from app.db.session import SessionLocal
from app.models.user import User
from app.services.auth_service import create_user
from app.services.user_management_service import (
    get_user,
    list_users,
    set_user_active_status,
    update_user_profile,
)


TEST_PREFIX = "user-management-test"
TEST_PASSWORD = "AAKAR-User-Management-123!"


def create_test_user(
    *,
    full_name: str,
    email: str | None = None,
) -> User:
    db = SessionLocal()

    try:
        return create_user(
            db=db,
            email=email
            or f"{TEST_PREFIX}-{uuid4()}@example.com",
            password=TEST_PASSWORD,
            full_name=full_name,
        )
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


def test_get_user_returns_existing_user():
    user = create_test_user(
        full_name="Existing User",
    )

    try:
        db = SessionLocal()

        try:
            result = get_user(
                db=db,
                user_id=user.id,
            )

            assert result is not None
            assert result.id == user.id
            assert result.full_name == "Existing User"
        finally:
            db.close()
    finally:
        delete_test_user(user.id)


def test_get_user_returns_none_for_unknown_user():
    db = SessionLocal()

    try:
        result = get_user(
            db=db,
            user_id=uuid4(),
        )

        assert result is None
    finally:
        db.close()


def test_list_users_returns_matching_search_results():
    first_user = create_test_user(
        full_name="Aakar Searchable Officer",
    )

    second_user = create_test_user(
        full_name="Completely Different User",
    )

    try:
        db = SessionLocal()

        try:
            users, total = list_users(
                db=db,
                search="searchable officer",
            )

            user_ids = {item.id for item in users}

            assert total >= 1
            assert first_user.id in user_ids
            assert second_user.id not in user_ids
        finally:
            db.close()
    finally:
        delete_test_user(first_user.id)
        delete_test_user(second_user.id)


def test_list_users_filters_by_active_status():
    active_user = create_test_user(
        full_name="Active Management User",
    )

    inactive_user = create_test_user(
        full_name="Inactive Management User",
    )

    db = SessionLocal()

    try:
        set_user_active_status(
            db=db,
            user_id=inactive_user.id,
            is_active=False,
        )
    finally:
        db.close()

    try:
        db = SessionLocal()

        try:
            users, _ = list_users(
                db=db,
                is_active=False,
            )

            user_ids = {item.id for item in users}

            assert inactive_user.id in user_ids
            assert active_user.id not in user_ids
        finally:
            db.close()
    finally:
        delete_test_user(active_user.id)
        delete_test_user(inactive_user.id)


def test_list_users_supports_pagination():
    first_user = create_test_user(
        full_name="Pagination One",
    )

    second_user = create_test_user(
        full_name="Pagination Two",
    )

    try:
        db = SessionLocal()

        try:
            users, total = list_users(
                db=db,
                search=TEST_PREFIX,
                offset=0,
                limit=1,
            )

            assert total >= 2
            assert len(users) == 1
        finally:
            db.close()
    finally:
        delete_test_user(first_user.id)
        delete_test_user(second_user.id)


def test_update_user_profile_normalizes_values():
    user = create_test_user(
        full_name="Old Name",
        email=f"{TEST_PREFIX}-{uuid4()}@example.com",
    )

    try:
        db = SessionLocal()

        try:
            updated_user = update_user_profile(
                db=db,
                user_id=user.id,
                full_name="  New User Name  ",
                email=f"  UPDATED-{uuid4()}@EXAMPLE.COM  ",
            )

            assert updated_user.full_name == "New User Name"
            assert updated_user.email.endswith("@example.com")
            assert updated_user.email == updated_user.email.lower()
        finally:
            db.close()
    finally:
        delete_test_user(user.id)


def test_update_user_profile_rejects_duplicate_email():
    first_user = create_test_user(
        full_name="First User",
        email=f"{TEST_PREFIX}-first-{uuid4()}@example.com",
    )

    second_user = create_test_user(
        full_name="Second User",
        email=f"{TEST_PREFIX}-second-{uuid4()}@example.com",
    )

    try:
        db = SessionLocal()

        try:
            with pytest.raises(ValueError, match="already exists"):
                update_user_profile(
                    db=db,
                    user_id=second_user.id,
                    full_name="Updated Second User",
                    email=first_user.email,
                )
        finally:
            db.close()
    finally:
        delete_test_user(first_user.id)
        delete_test_user(second_user.id)


def test_update_unknown_user_raises_error():
    db = SessionLocal()

    try:
        with pytest.raises(ValueError, match="User not found"):
            update_user_profile(
                db=db,
                user_id=uuid4(),
                full_name="Unknown User",
                email="unknown@example.com",
            )
    finally:
        db.close()


def test_set_user_active_status_changes_account_state():
    user = create_test_user(
        full_name="Status Management User",
    )

    try:
        db = SessionLocal()

        try:
            updated_user = set_user_active_status(
                db=db,
                user_id=user.id,
                is_active=False,
            )

            assert updated_user.is_active is False

            updated_user = set_user_active_status(
                db=db,
                user_id=user.id,
                is_active=True,
            )

            assert updated_user.is_active is True
        finally:
            db.close()
    finally:
        delete_test_user(user.id)


def test_set_user_active_status_unknown_user_raises_error():
    db = SessionLocal()

    try:
        with pytest.raises(ValueError, match="User not found"):
            set_user_active_status(
                db=db,
                user_id=uuid4(),
                is_active=False,
            )
    finally:
        db.close()
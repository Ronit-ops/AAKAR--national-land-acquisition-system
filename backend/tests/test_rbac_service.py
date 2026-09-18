from sqlalchemy import delete

from app.db.session import SessionLocal
from app.models.user import User
from app.models.user_role import UserRole
from app.services.auth_service import create_user
from app.services.rbac_service import (
    assign_role,
    get_role_by_code,
    get_user_role_codes,
    get_user_roles,
    remove_role,
    user_has_role,
)


TEST_EMAIL = "rbac-service-test@example.com"
TEST_PASSWORD = "AAKAR-RBAC-Test-123!"
TEST_NAME = "RBAC Service Test User"


def cleanup_test_user() -> None:
    """Remove the RBAC test user and role assignments."""
    db = SessionLocal()

    try:
        user = db.scalar(
            __import__("sqlalchemy").select(User).where(
                User.email == TEST_EMAIL,
            )
        )

        if user is not None:
            db.execute(
                delete(UserRole).where(
                    UserRole.user_id == user.id,
                )
            )

            db.delete(user)
            db.commit()
    finally:
        db.close()


def test_get_existing_role_by_code():
    db = SessionLocal()

    try:
        role = get_role_by_code(
            db=db,
            role_code=" NATIONAL_ADMINISTRATOR ",
        )

        assert role is not None
        assert role.code == "national_administrator"
        assert role.name == "National Administrator"
        assert role.scope_level == "national"
        assert role.is_active is True
    finally:
        db.close()


def test_get_missing_role_by_code():
    db = SessionLocal()

    try:
        role = get_role_by_code(
            db=db,
            role_code="role-that-does-not-exist",
        )

        assert role is None
    finally:
        db.close()


def test_assign_role_and_check_membership():
    cleanup_test_user()

    db = SessionLocal()

    try:
        user = create_user(
            db=db,
            email=TEST_EMAIL,
            password=TEST_PASSWORD,
            full_name=TEST_NAME,
        )

        assignment = assign_role(
            db=db,
            user_id=user.id,
            role_code="land_acquisition_officer",
        )

        assert assignment.user_id == user.id
        assert assignment.role_id is not None

        assert user_has_role(
            db=db,
            user_id=user.id,
            role_code="LAND_ACQUISITION_OFFICER",
        )

        role_codes = get_user_role_codes(
            db=db,
            user_id=user.id,
        )

        assert role_codes == {"land_acquisition_officer"}
    finally:
        db.close()
        cleanup_test_user()


def test_assigning_same_role_is_idempotent():
    cleanup_test_user()

    db = SessionLocal()

    try:
        user = create_user(
            db=db,
            email=TEST_EMAIL,
            password=TEST_PASSWORD,
            full_name=TEST_NAME,
        )

        first_assignment = assign_role(
            db=db,
            user_id=user.id,
            role_code="district_collector",
        )

        second_assignment = assign_role(
            db=db,
            user_id=user.id,
            role_code="district_collector",
        )

        assert first_assignment.user_id == second_assignment.user_id
        assert first_assignment.role_id == second_assignment.role_id

        roles = get_user_roles(
            db=db,
            user_id=user.id,
        )

        assert len(roles) == 1
        assert roles[0].code == "district_collector"
    finally:
        db.close()
        cleanup_test_user()


def test_user_can_have_multiple_roles():
    cleanup_test_user()

    db = SessionLocal()

    try:
        user = create_user(
            db=db,
            email=TEST_EMAIL,
            password=TEST_PASSWORD,
            full_name=TEST_NAME,
        )

        assign_role(
            db=db,
            user_id=user.id,
            role_code="state_nodal_officer",
        )

        assign_role(
            db=db,
            user_id=user.id,
            role_code="land_acquisition_officer",
        )

        role_codes = get_user_role_codes(
            db=db,
            user_id=user.id,
        )

        assert role_codes == {
            "state_nodal_officer",
            "land_acquisition_officer",
        }
    finally:
        db.close()
        cleanup_test_user()


def test_remove_role():
    cleanup_test_user()

    db = SessionLocal()

    try:
        user = create_user(
            db=db,
            email=TEST_EMAIL,
            password=TEST_PASSWORD,
            full_name=TEST_NAME,
        )

        assign_role(
            db=db,
            user_id=user.id,
            role_code="revenue_officer",
        )

        assert user_has_role(
            db=db,
            user_id=user.id,
            role_code="revenue_officer",
        )

        removed = remove_role(
            db=db,
            user_id=user.id,
            role_code="REVENUE_OFFICER",
        )

        assert removed is True

        assert not user_has_role(
            db=db,
            user_id=user.id,
            role_code="revenue_officer",
        )
    finally:
        db.close()
        cleanup_test_user()


def test_remove_missing_role_returns_false():
    cleanup_test_user()

    db = SessionLocal()

    try:
        user = create_user(
            db=db,
            email=TEST_EMAIL,
            password=TEST_PASSWORD,
            full_name=TEST_NAME,
        )

        removed = remove_role(
            db=db,
            user_id=user.id,
            role_code="revenue_officer",
        )

        assert removed is False
    finally:
        db.close()
        cleanup_test_user()
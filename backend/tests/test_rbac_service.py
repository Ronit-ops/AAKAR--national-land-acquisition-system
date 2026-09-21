from uuid import uuid4

from sqlalchemy import delete, select

from app.db.session import SessionLocal
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.user import User
from app.models.user_role import UserRole
from app.services.auth_service import create_user
from app.services.rbac_service import (
    assign_permission_to_role,
    assign_role,
    get_permission_by_code,
    get_user_permission_codes,
    get_user_permissions,
    get_role_by_code,
    get_user_role_codes,
    get_user_roles,
    remove_permission_from_role,
    remove_role,
    user_has_permission,
    user_has_role,
)


TEST_EMAIL = "rbac-service-test@example.com"
TEST_PASSWORD = "AAKAR-RBAC-Test-123!"
TEST_NAME = "RBAC Service Test User"

TEST_PERMISSION_CODE = "test.permission.read"
TEST_PERMISSION_NAME = "Test Permission Read"
TEST_PERMISSION_RESOURCE = "test"
TEST_PERMISSION_ACTION = "read"


def cleanup_test_user() -> None:
    """Remove the RBAC test user and role assignments."""
    db = SessionLocal()

    try:
        user = db.scalar(
            select(User).where(
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


def cleanup_test_permission() -> None:
    """Remove the temporary permission and its role assignments."""
    db = SessionLocal()

    try:
        permission = db.scalar(
            select(Permission).where(
                Permission.code == TEST_PERMISSION_CODE,
            )
        )

        if permission is not None:
            db.execute(
                delete(RolePermission).where(
                    RolePermission.permission_id == permission.id,
                )
            )

            db.delete(permission)
            db.commit()
    finally:
        db.close()


def create_test_permission() -> Permission:
    """Create the temporary permission used by permission-service tests."""
    cleanup_test_permission()

    db = SessionLocal()

    try:
        permission = Permission(
            code=TEST_PERMISSION_CODE,
            name=TEST_PERMISSION_NAME,
            resource=TEST_PERMISSION_RESOURCE,
            action=TEST_PERMISSION_ACTION,
            description="Temporary permission for RBAC service tests.",
            is_system_permission=False,
            is_active=True,
        )

        db.add(permission)
        db.commit()
        db.refresh(permission)

        return permission
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


def test_get_existing_permission_by_code():
    permission = create_test_permission()
    db = SessionLocal()

    try:
        result = get_permission_by_code(
            db=db,
            permission_code=" TEST.PERMISSION.READ ",
        )

        assert result is not None
        assert result.id == permission.id
        assert result.code == TEST_PERMISSION_CODE
        assert result.resource == TEST_PERMISSION_RESOURCE
        assert result.action == TEST_PERMISSION_ACTION
        assert result.is_active is True
    finally:
        db.close()
        cleanup_test_permission()


def test_get_missing_permission_by_code():
    db = SessionLocal()

    try:
        result = get_permission_by_code(
            db=db,
            permission_code="permission-that-does-not-exist",
        )

        assert result is None
    finally:
        db.close()


def test_inactive_permission_is_not_returned():
    permission = create_test_permission()
    db = SessionLocal()

    try:
        stored_permission = db.get(Permission, permission.id)
        assert stored_permission is not None

        stored_permission.is_active = False
        db.commit()

        result = get_permission_by_code(
            db=db,
            permission_code=TEST_PERMISSION_CODE,
        )

        assert result is None
    finally:
        db.close()
        cleanup_test_permission()


def test_assign_permission_to_role_and_check_user_permission():
    cleanup_test_user()
    permission = create_test_permission()

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
            role_code="district_collector",
        )

        assignment = assign_permission_to_role(
            db=db,
            role_code="DISTRICT_COLLECTOR",
            permission_code="TEST.PERMISSION.READ",
        )

        assert assignment.role_id is not None
        assert assignment.permission_id == permission.id

        assert user_has_permission(
            db=db,
            user_id=user.id,
            permission_code=TEST_PERMISSION_CODE,
        )

        permission_codes = get_user_permission_codes(
            db=db,
            user_id=user.id,
        )

        assert permission_codes == {TEST_PERMISSION_CODE}
    finally:
        db.close()
        cleanup_test_user()
        cleanup_test_permission()


def test_assigning_same_permission_is_idempotent():
    cleanup_test_user()
    permission = create_test_permission()

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
            role_code="district_collector",
        )

        first_assignment = assign_permission_to_role(
            db=db,
            role_code="district_collector",
            permission_code=TEST_PERMISSION_CODE,
        )

        second_assignment = assign_permission_to_role(
            db=db,
            role_code="district_collector",
            permission_code=TEST_PERMISSION_CODE,
        )

        assert first_assignment.role_id == second_assignment.role_id
        assert first_assignment.permission_id == second_assignment.permission_id
    finally:
        db.close()
        cleanup_test_user()
        cleanup_test_permission()


def test_user_can_receive_permissions_from_multiple_roles():
    cleanup_test_user()
    permission = create_test_permission()

    second_permission_code = "test.permission.write"

    cleanup_db = SessionLocal()

    try:
        second_permission = cleanup_db.scalar(
            select(Permission).where(
                Permission.code == second_permission_code,
            )
        )

        if second_permission is None:
            second_permission = Permission(
                code=second_permission_code,
                name="Test Permission Write",
                resource=TEST_PERMISSION_RESOURCE,
                action="write",
                description="Temporary second permission for RBAC service tests.",
                is_system_permission=False,
                is_active=True,
            )
            cleanup_db.add(second_permission)
            cleanup_db.commit()
            cleanup_db.refresh(second_permission)
    finally:
        cleanup_db.close()

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
            role_code="district_collector",
        )

        assign_role(
            db=db,
            user_id=user.id,
            role_code="state_nodal_officer",
        )

        assign_permission_to_role(
            db=db,
            role_code="district_collector",
            permission_code=TEST_PERMISSION_CODE,
        )

        assign_permission_to_role(
            db=db,
            role_code="state_nodal_officer",
            permission_code=second_permission_code,
        )

        permission_codes = get_user_permission_codes(
            db=db,
            user_id=user.id,
        )

        assert permission_codes == {
            TEST_PERMISSION_CODE,
            second_permission_code,
        }

        permissions = get_user_permissions(
            db=db,
            user_id=user.id,
        )

        assert {item.code for item in permissions} == {
            TEST_PERMISSION_CODE,
            second_permission_code,
        }
    finally:
        db.close()
        cleanup_test_user()

        cleanup_db = SessionLocal()

        try:
            second_permission = cleanup_db.scalar(
                select(Permission).where(
                    Permission.code == second_permission_code,
                )
            )

            if second_permission is not None:
                cleanup_db.execute(
                    delete(RolePermission).where(
                        RolePermission.permission_id == second_permission.id,
                    )
                )
                cleanup_db.delete(second_permission)
                cleanup_db.commit()
        finally:
            cleanup_db.close()

        cleanup_test_permission()


def test_permission_requires_active_role():
    cleanup_test_user()
    permission = create_test_permission()

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
            role_code="district_collector",
        )

        assign_permission_to_role(
            db=db,
            role_code="district_collector",
            permission_code=TEST_PERMISSION_CODE,
        )

        role = db.scalar(
            select(Role).where(
                Role.code == "district_collector",
            )
        )

        assert role is not None

        role.is_active = False
        db.commit()

        assert not user_has_permission(
            db=db,
            user_id=user.id,
            permission_code=TEST_PERMISSION_CODE,
        )

        assert get_user_permission_codes(
            db=db,
            user_id=user.id,
        ) == set()
    finally:
        db.close()
        cleanup_test_user()

        db = SessionLocal()

        try:
            role = db.scalar(
                select(Role).where(
                    Role.code == "district_collector",
                )
            )

            if role is not None:
                role.is_active = True
                db.commit()
        finally:
            db.close()

        cleanup_test_permission()


def test_remove_permission_from_role():
    cleanup_test_user()
    permission = create_test_permission()

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

        assign_permission_to_role(
            db=db,
            role_code="revenue_officer",
            permission_code=TEST_PERMISSION_CODE,
        )

        assert user_has_permission(
            db=db,
            user_id=user.id,
            permission_code=TEST_PERMISSION_CODE,
        )

        removed = remove_permission_from_role(
            db=db,
            role_code="REVENUE_OFFICER",
            permission_code="TEST.PERMISSION.READ",
        )

        assert removed is True

        assert not user_has_permission(
            db=db,
            user_id=user.id,
            permission_code=TEST_PERMISSION_CODE,
        )
    finally:
        db.close()
        cleanup_test_user()
        cleanup_test_permission()


def test_remove_missing_permission_assignment_returns_false():
    cleanup_test_user()
    create_test_permission()

    db = SessionLocal()

    try:
        user = create_user(
            db=db,
            email=TEST_EMAIL,
            password=TEST_PASSWORD,
            full_name=TEST_NAME,
        )

        removed = remove_permission_from_role(
            db=db,
            role_code="revenue_officer",
            permission_code=TEST_PERMISSION_CODE,
        )

        assert removed is False
    finally:
        db.close()
        cleanup_test_user()
        cleanup_test_permission()
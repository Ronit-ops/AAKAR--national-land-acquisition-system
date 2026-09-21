from typing import Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.api.deps import require_any_permission, require_permission
from app.core.jwt import create_access_token
from app.db.session import SessionLocal
from app.models.permission import Permission
from app.models.role_permission import RolePermission
from app.models.user import User
from app.services.auth_service import create_user
from app.services.rbac_service import (
    assign_permission_to_role,
    assign_role,
    remove_permission_from_role,
)


TEST_EMAIL_PREFIX = "permission-dependency-test"
TEST_PASSWORD = "AAKAR-Permission-Dependency-123!"

TEST_PERMISSION_CODE = "test.permission.access"
TEST_PERMISSION_NAME = "Test Permission Access"

SECOND_PERMISSION_CODE = "test.permission.secondary"


def create_test_user() -> User:
    """Create a temporary user for permission dependency tests."""
    db = SessionLocal()

    try:
        user = create_user(
            db=db,
            email=f"{TEST_EMAIL_PREFIX}-{uuid4()}@example.com",
            password=TEST_PASSWORD,
            full_name="Permission Dependency Test User",
        )

        return user
    finally:
        db.close()


def delete_test_user(user_id) -> None:
    """Delete a temporary test user."""
    db = SessionLocal()

    try:
        user = db.get(User, user_id)

        if user is not None:
            db.delete(user)
            db.commit()
    finally:
        db.close()


def create_test_permissions() -> None:
    """Create the temporary permissions used by dependency tests."""
    delete_test_permissions()

    db = SessionLocal()

    try:
        db.add_all(
            [
                Permission(
                    code=TEST_PERMISSION_CODE,
                    name=TEST_PERMISSION_NAME,
                    resource="test",
                    action="access",
                    description="Temporary permission dependency test.",
                    is_system_permission=False,
                    is_active=True,
                ),
                Permission(
                    code=SECOND_PERMISSION_CODE,
                    name="Test Secondary Permission",
                    resource="test",
                    action="secondary",
                    description="Temporary secondary dependency permission.",
                    is_system_permission=False,
                    is_active=True,
                ),
            ]
        )

        db.commit()
    finally:
        db.close()


def delete_test_permissions() -> None:
    """Delete temporary permissions and their role assignments."""
    db = SessionLocal()

    try:
        permissions = list(
            db.scalars(
                select(Permission).where(
                    Permission.code.in_(
                        [
                            TEST_PERMISSION_CODE,
                            SECOND_PERMISSION_CODE,
                        ]
                    )
                )
            ).all()
        )

        permission_ids = [
            permission.id
            for permission in permissions
        ]

        if permission_ids:
            db.execute(
                delete(RolePermission).where(
                    RolePermission.permission_id.in_(permission_ids)
                )
            )

            db.execute(
                delete(Permission).where(
                    Permission.id.in_(permission_ids)
                )
            )

            db.commit()
    finally:
        db.close()


app = FastAPI()


@app.get("/test/permission")
def permission_endpoint(
    current_user: Annotated[
        User,
        Depends(require_permission(TEST_PERMISSION_CODE)),
    ],
):
    return {
        "user_id": str(current_user.id),
        "authorized": True,
    }


@app.get("/test/any-permission")
def any_permission_endpoint(
    current_user: Annotated[
        User,
        Depends(
            require_any_permission(
                TEST_PERMISSION_CODE,
                SECOND_PERMISSION_CODE,
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
    response = client.get("/test/permission")

    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials."


def test_user_without_permission_gets_403():
    create_test_permissions()
    user = create_test_user()

    try:
        token = login_and_get_token(user)

        response = client.get(
            "/test/permission",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403
        assert (
            response.json()["detail"]
            == "You do not have permission to access this resource."
        )
    finally:
        delete_test_user(user.id)
        delete_test_permissions()


def test_user_with_permission_gets_200():
    create_test_permissions()
    user = create_test_user()

    db = SessionLocal()

    try:
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
    finally:
        db.close()

    try:
        token = login_and_get_token(user)

        response = client.get(
            "/test/permission",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json()["authorized"] is True
        assert response.json()["user_id"] == str(user.id)
    finally:
        delete_test_user(user.id)
        delete_test_permissions()


def test_permission_matching_is_case_insensitive():
    create_test_permissions()
    user = create_test_user()

    db = SessionLocal()

    try:
        assign_role(
            db=db,
            user_id=user.id,
            role_code="district_collector",
        )

        assign_permission_to_role(
            db=db,
            role_code="district_collector",
            permission_code="TEST.PERMISSION.ACCESS",
        )
    finally:
        db.close()

    try:
        token = login_and_get_token(user)

        response = client.get(
            "/test/permission",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
    finally:
        delete_test_user(user.id)
        delete_test_permissions()


def test_any_permission_allows_matching_permission():
    create_test_permissions()
    user = create_test_user()

    db = SessionLocal()

    try:
        assign_role(
            db=db,
            user_id=user.id,
            role_code="district_collector",
        )

        assign_permission_to_role(
            db=db,
            role_code="district_collector",
            permission_code=SECOND_PERMISSION_CODE,
        )
    finally:
        db.close()

    try:
        token = login_and_get_token(user)

        response = client.get(
            "/test/any-permission",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json()["authorized"] is True
    finally:
        delete_test_user(user.id)
        delete_test_permissions()


def test_any_permission_returns_403_when_none_match():
    create_test_permissions()
    user = create_test_user()

    try:
        token = login_and_get_token(user)

        response = client.get(
            "/test/any-permission",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403
    finally:
        delete_test_user(user.id)
        delete_test_permissions()


def test_permission_assignment_takes_effect_without_new_token():
    create_test_permissions()
    user = create_test_user()

    db = SessionLocal()

    try:
        assign_role(
            db=db,
            user_id=user.id,
            role_code="district_collector",
        )

        token = login_and_get_token(user)

        first_response = client.get(
            "/test/permission",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert first_response.status_code == 403

        assign_permission_to_role(
            db=db,
            role_code="district_collector",
            permission_code=TEST_PERMISSION_CODE,
        )

        second_response = client.get(
            "/test/permission",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert second_response.status_code == 200
    finally:
        db.close()
        delete_test_user(user.id)
        delete_test_permissions()


def test_removed_permission_is_immediately_denied():
    create_test_permissions()
    user = create_test_user()

    db = SessionLocal()

    try:
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

        token = login_and_get_token(user)

        authorized_response = client.get(
            "/test/permission",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert authorized_response.status_code == 200

        removed = remove_permission_from_role(
            db=db,
            role_code="district_collector",
            permission_code=TEST_PERMISSION_CODE,
        )

        assert removed is True

        denied_response = client.get(
            "/test/permission",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert denied_response.status_code == 403
    finally:
        db.close()
        delete_test_user(user.id)
        delete_test_permissions()
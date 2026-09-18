from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.jwt import create_access_token
from app.db.session import SessionLocal
from app.main import app
from app.models.user import User
from app.services.auth_service import create_user
from app.services.rbac_service import assign_role


client = TestClient(app)

TEST_PASSWORD = "AAKAR-User-Management-API-123!"


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
            or f"user-management-api-{uuid4()}@example.com",
            password=TEST_PASSWORD,
            full_name=full_name,
        )
    finally:
        db.close()


def create_system_administrator() -> User:
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
    token = create_access_token(user.id)

    return {
        "Authorization": f"Bearer {token}",
    }


def test_user_list_requires_authentication():
    response = client.get("/api/v1/users")

    assert response.status_code == 401


def test_user_list_forbids_non_administrator():
    user = create_test_user(
        full_name="Regular User",
    )

    try:
        response = client.get(
            "/api/v1/users",
            headers=auth_headers(user),
        )

        assert response.status_code == 403
    finally:
        delete_test_user(user.id)


def test_system_administrator_can_list_users():
    admin = create_system_administrator()
    target = create_test_user(
        full_name="Managed User",
    )

    try:
        response = client.get(
            "/api/v1/users",
            headers=auth_headers(admin),
        )

        assert response.status_code == 200

        body = response.json()

        assert "items" in body
        assert "total" in body
        assert "offset" in body
        assert "limit" in body

        assert any(
            item["id"] == str(target.id)
            for item in body["items"]
        )

        for item in body["items"]:
            assert "password_hash" not in item
    finally:
        delete_test_user(admin.id)
        delete_test_user(target.id)


def test_system_administrator_can_search_users():
    admin = create_system_administrator()
    target = create_test_user(
        full_name="Unique Search Officer",
    )

    try:
        response = client.get(
            "/api/v1/users",
            params={"search": "Unique Search Officer"},
            headers=auth_headers(admin),
        )

        assert response.status_code == 200

        body = response.json()

        assert body["total"] >= 1
        assert any(
            item["id"] == str(target.id)
            for item in body["items"]
        )
    finally:
        delete_test_user(admin.id)
        delete_test_user(target.id)


def test_system_administrator_can_get_user_details():
    admin = create_system_administrator()
    target = create_test_user(
        full_name="User Detail Target",
    )

    try:
        response = client.get(
            f"/api/v1/users/{target.id}",
            headers=auth_headers(admin),
        )

        assert response.status_code == 200

        body = response.json()

        assert body["id"] == str(target.id)
        assert body["full_name"] == "User Detail Target"
        assert body["email"] == target.email
        assert "password_hash" not in body
    finally:
        delete_test_user(admin.id)
        delete_test_user(target.id)


def test_unknown_user_returns_404():
    admin = create_system_administrator()

    try:
        response = client.get(
            f"/api/v1/users/{uuid4()}",
            headers=auth_headers(admin),
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "User not found."
    finally:
        delete_test_user(admin.id)


def test_system_administrator_can_create_user():
    admin = create_system_administrator()
    email = f"created-user-{uuid4()}@example.com"

    created_user_id = None

    try:
        response = client.post(
            "/api/v1/users",
            headers=auth_headers(admin),
            json={
                "email": email,
                "password": TEST_PASSWORD,
                "full_name": "Created Managed User",
            },
        )

        assert response.status_code == 201

        body = response.json()

        assert body["email"] == email
        assert body["full_name"] == "Created Managed User"
        assert body["is_active"] is True
        assert "password_hash" not in body

        created_user_id = body["id"]
    finally:
        if created_user_id is not None:
            delete_test_user(created_user_id)

        delete_test_user(admin.id)


def test_duplicate_email_returns_409():
    admin = create_system_administrator()
    target = create_test_user(
        full_name="Existing Email User",
    )

    try:
        response = client.post(
            "/api/v1/users",
            headers=auth_headers(admin),
            json={
                "email": target.email,
                "password": TEST_PASSWORD,
                "full_name": "Duplicate Email User",
            },
        )

        assert response.status_code == 409
        assert (
            response.json()["detail"]
            == "A user with this email already exists."
        )
    finally:
        delete_test_user(admin.id)
        delete_test_user(target.id)


def test_invalid_create_request_returns_422():
    admin = create_system_administrator()

    try:
        response = client.post(
            "/api/v1/users",
            headers=auth_headers(admin),
            json={
                "email": "not-an-email",
                "password": "short",
                "full_name": "A",
            },
        )

        assert response.status_code == 422
    finally:
        delete_test_user(admin.id)


def test_system_administrator_can_update_user():
    admin = create_system_administrator()
    target = create_test_user(
        full_name="Original User",
    )

    new_email = f"updated-user-{uuid4()}@example.com"

    try:
        response = client.patch(
            f"/api/v1/users/{target.id}",
            headers=auth_headers(admin),
            json={
                "email": new_email,
                "full_name": "Updated User",
            },
        )

        assert response.status_code == 200

        body = response.json()

        assert body["id"] == str(target.id)
        assert body["email"] == new_email
        assert body["full_name"] == "Updated User"
    finally:
        delete_test_user(admin.id)
        delete_test_user(target.id)


def test_update_duplicate_email_returns_409():
    admin = create_system_administrator()
    first_user = create_test_user(
        full_name="First Managed User",
    )
    second_user = create_test_user(
        full_name="Second Managed User",
    )

    try:
        response = client.patch(
            f"/api/v1/users/{second_user.id}",
            headers=auth_headers(admin),
            json={
                "email": first_user.email,
                "full_name": "Updated Second User",
            },
        )

        assert response.status_code == 409
        assert (
            response.json()["detail"]
            == "A user with this email already exists."
        )
    finally:
        delete_test_user(admin.id)
        delete_test_user(first_user.id)
        delete_test_user(second_user.id)


def test_system_administrator_can_deactivate_user():
    admin = create_system_administrator()
    target = create_test_user(
        full_name="Status Target",
    )

    try:
        response = client.patch(
            f"/api/v1/users/{target.id}/status",
            headers=auth_headers(admin),
            json={
                "is_active": False,
            },
        )

        assert response.status_code == 200
        assert response.json()["is_active"] is False
    finally:
        delete_test_user(admin.id)
        delete_test_user(target.id)


def test_system_administrator_can_activate_user():
    admin = create_system_administrator()
    target = create_test_user(
        full_name="Inactive Status Target",
    )

    db = SessionLocal()

    try:
        target.is_active = False
        db.commit()
    finally:
        db.close()

    try:
        response = client.patch(
            f"/api/v1/users/{target.id}/status",
            headers=auth_headers(admin),
            json={
                "is_active": True,
            },
        )

        assert response.status_code == 200
        assert response.json()["is_active"] is True
    finally:
        delete_test_user(admin.id)
        delete_test_user(target.id)


def test_system_administrator_cannot_change_own_active_status():
    admin = create_system_administrator()

    try:
        response = client.patch(
            f"/api/v1/users/{admin.id}/status",
            headers=auth_headers(admin),
            json={
                "is_active": False,
            },
        )

        assert response.status_code == 400
        assert (
            response.json()["detail"]
            == "A system administrator cannot change their own active status."
        )
    finally:
        delete_test_user(admin.id)


def test_status_change_for_unknown_user_returns_404():
    admin = create_system_administrator()

    try:
        response = client.patch(
            f"/api/v1/users/{uuid4()}/status",
            headers=auth_headers(admin),
            json={
                "is_active": False,
            },
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "User not found."
    finally:
        delete_test_user(admin.id)


def test_non_administrator_cannot_update_user():
    user = create_test_user(
        full_name="Regular Operator",
    )
    target = create_test_user(
        full_name="Protected Target",
    )

    try:
        response = client.patch(
            f"/api/v1/users/{target.id}",
            headers=auth_headers(user),
            json={
                "email": f"blocked-{uuid4()}@example.com",
                "full_name": "Unauthorized Update",
            },
        )

        assert response.status_code == 403
    finally:
        delete_test_user(user.id)
        delete_test_user(target.id)
from app.models.authority import Authority
from app.models.department import Department
from app.services.authority_service import create_authority
from app.services.department_service import create_department


def create_test_department(
    *,
    name: str = "API Test Department",
    is_active: bool = True,
) -> Department:
    db = SessionLocal()

    try:
        department = create_department(
            db=db,
            code=f"DPT-{uuid4().hex[:8].upper()}",
            name=name,
        )

        if not is_active:
            department.is_active = False
            db.commit()
            db.refresh(department)

        return department
    finally:
        db.close()


def create_test_authority(
    *,
    department_id,
    name: str = "API Test Authority",
    is_active: bool = True,
) -> Authority:
    db = SessionLocal()

    try:
        authority = create_authority(
            db=db,
            department_id=department_id,
            code=f"AUTH-{uuid4().hex[:8].upper()}",
            name=name,
            authority_type="STATE",
        )

        if not is_active:
            authority.is_active = False
            db.commit()
            db.refresh(authority)

        return authority
    finally:
        db.close()


def delete_test_authority(authority_id) -> None:
    db = SessionLocal()

    try:
        authority = db.get(Authority, authority_id)

        if authority is not None:
            db.delete(authority)

        db.commit()
    finally:
        db.close()


def delete_test_department(department_id) -> None:
    db = SessionLocal()

    try:
        department = db.get(Department, department_id)

        if department is not None:
            db.delete(department)

        db.commit()
    finally:
        db.close()


def test_system_administrator_can_assign_user_organization():
    admin = create_system_administrator()
    target = create_test_user(
        full_name="Organization Assignment Target",
    )
    department = create_test_department()
    authority = create_test_authority(
        department_id=department.id,
    )

    try:
        response = client.patch(
            f"/api/v1/users/{target.id}/organization",
            headers=auth_headers(admin),
            json={
                "department_id": str(department.id),
                "authority_id": str(authority.id),
            },
        )

        assert response.status_code == 200

        body = response.json()

        assert body["id"] == str(target.id)

        db = SessionLocal()

        try:
            updated_user = db.get(User, target.id)

            assert updated_user is not None
            assert updated_user.department_id == department.id
            assert updated_user.authority_id == authority.id
        finally:
            db.close()
    finally:
        delete_test_user(admin.id)
        delete_test_user(target.id)
        delete_test_authority(authority.id)
        delete_test_department(department.id)


def test_system_administrator_can_assign_department_without_authority():
    admin = create_system_administrator()
    target = create_test_user(
        full_name="Department Only Target",
    )
    department = create_test_department()

    try:
        response = client.patch(
            f"/api/v1/users/{target.id}/organization",
            headers=auth_headers(admin),
            json={
                "department_id": str(department.id),
                "authority_id": None,
            },
        )

        assert response.status_code == 200

        db = SessionLocal()

        try:
            updated_user = db.get(User, target.id)

            assert updated_user is not None
            assert updated_user.department_id == department.id
            assert updated_user.authority_id is None
        finally:
            db.close()
    finally:
        delete_test_user(admin.id)
        delete_test_user(target.id)
        delete_test_department(department.id)


def test_system_administrator_can_clear_user_organization():
    admin = create_system_administrator()
    target = create_test_user(
        full_name="Organization Clear Target",
    )
    department = create_test_department()
    authority = create_test_authority(
        department_id=department.id,
    )

    try:
        setup_response = client.patch(
            f"/api/v1/users/{target.id}/organization",
            headers=auth_headers(admin),
            json={
                "department_id": str(department.id),
                "authority_id": str(authority.id),
            },
        )

        assert setup_response.status_code == 200

        response = client.patch(
            f"/api/v1/users/{target.id}/organization",
            headers=auth_headers(admin),
            json={
                "department_id": None,
                "authority_id": None,
            },
        )

        assert response.status_code == 200

        db = SessionLocal()

        try:
            updated_user = db.get(User, target.id)

            assert updated_user is not None
            assert updated_user.department_id is None
            assert updated_user.authority_id is None
        finally:
            db.close()
    finally:
        delete_test_user(admin.id)
        delete_test_user(target.id)
        delete_test_authority(authority.id)
        delete_test_department(department.id)


def test_organization_rejects_authority_without_department():
    admin = create_system_administrator()
    target = create_test_user(
        full_name="Authority Without Department Target",
    )
    department = create_test_department()
    authority = create_test_authority(
        department_id=department.id,
    )

    try:
        response = client.patch(
            f"/api/v1/users/{target.id}/organization",
            headers=auth_headers(admin),
            json={
                "department_id": None,
                "authority_id": str(authority.id),
            },
        )

        assert response.status_code == 422
        assert response.json()["detail"] == "An authority requires a department."
    finally:
        delete_test_user(admin.id)
        delete_test_user(target.id)
        delete_test_authority(authority.id)
        delete_test_department(department.id)


def test_organization_rejects_inactive_department():
    admin = create_system_administrator()
    target = create_test_user(
        full_name="Inactive Department Target",
    )
    department = create_test_department(
        is_active=False,
    )

    try:
        response = client.patch(
            f"/api/v1/users/{target.id}/organization",
            headers=auth_headers(admin),
            json={
                "department_id": str(department.id),
                "authority_id": None,
            },
        )

        assert response.status_code == 422
        assert (
            response.json()["detail"]
            == "Cannot assign a user to an inactive department."
        )
    finally:
        delete_test_user(admin.id)
        delete_test_user(target.id)
        delete_test_department(department.id)


def test_organization_rejects_inactive_authority():
    admin = create_system_administrator()
    target = create_test_user(
        full_name="Inactive Authority Target",
    )
    department = create_test_department()
    authority = create_test_authority(
        department_id=department.id,
        is_active=False,
    )

    try:
        response = client.patch(
            f"/api/v1/users/{target.id}/organization",
            headers=auth_headers(admin),
            json={
                "department_id": str(department.id),
                "authority_id": str(authority.id),
            },
        )

        assert response.status_code == 422
        assert (
            response.json()["detail"]
            == "Cannot assign a user to an inactive authority."
        )
    finally:
        delete_test_user(admin.id)
        delete_test_user(target.id)
        delete_test_authority(authority.id)
        delete_test_department(department.id)


def test_organization_rejects_authority_from_different_department():
    admin = create_system_administrator()
    target = create_test_user(
        full_name="Mismatched Authority Target",
    )
    first_department = create_test_department(
        name="First API Department",
    )
    second_department = create_test_department(
        name="Second API Department",
    )
    authority = create_test_authority(
        department_id=second_department.id,
    )

    try:
        response = client.patch(
            f"/api/v1/users/{target.id}/organization",
            headers=auth_headers(admin),
            json={
                "department_id": str(first_department.id),
                "authority_id": str(authority.id),
            },
        )

        assert response.status_code == 422
        assert (
            response.json()["detail"]
            == "Authority does not belong to the selected department."
        )
    finally:
        delete_test_user(admin.id)
        delete_test_user(target.id)
        delete_test_authority(authority.id)
        delete_test_department(first_department.id)
        delete_test_department(second_department.id)


def test_organization_unknown_user_returns_404():
    admin = create_system_administrator()
    department = create_test_department()

    try:
        response = client.patch(
            f"/api/v1/users/{uuid4()}/organization",
            headers=auth_headers(admin),
            json={
                "department_id": str(department.id),
                "authority_id": None,
            },
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "User not found."
    finally:
        delete_test_user(admin.id)
        delete_test_department(department.id)


def test_non_administrator_cannot_update_user_organization():
    user = create_test_user(
        full_name="Regular Organization Operator",
    )
    target = create_test_user(
        full_name="Protected Organization Target",
    )
    department = create_test_department()

    try:
        response = client.patch(
            f"/api/v1/users/{target.id}/organization",
            headers=auth_headers(user),
            json={
                "department_id": str(department.id),
                "authority_id": None,
            },
        )

        assert response.status_code == 403
    finally:
        delete_test_user(user.id)
        delete_test_user(target.id)
        delete_test_department(department.id)

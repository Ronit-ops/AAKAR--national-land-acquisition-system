from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.jwt import create_access_token
from app.db.session import SessionLocal
from app.main import app
from app.models.department import Department
from app.models.user import User
from app.services.auth_service import create_user
from app.services.department_service import create_department
from app.services.rbac_service import assign_role


client = TestClient(app)

TEST_PASSWORD = "AAKAR-Department-API-123!"


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
            or f"department-api-{uuid4()}@example.com",
            password=TEST_PASSWORD,
            full_name=full_name,
        )
    finally:
        db.close()


def create_system_administrator() -> User:
    user = create_test_user(
        full_name="Department API Administrator",
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


def create_test_department(
    *,
    code: str | None = None,
    name: str = "Test Department",
) -> Department:
    db = SessionLocal()

    try:
        return create_department(
            db=db,
            code=code or f"DPT-{uuid4().hex[:8].upper()}",
            name=name,
            description="Test department",
        )
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


def test_department_list_requires_authentication():
    response = client.get("/api/v1/departments")

    assert response.status_code == 401


def test_department_list_forbids_non_administrator():
    user = create_test_user(
        full_name="Regular Department User",
    )

    try:
        response = client.get(
            "/api/v1/departments",
            headers=auth_headers(user),
        )

        assert response.status_code == 403
    finally:
        delete_test_user(user.id)


def test_system_administrator_can_list_departments():
    admin = create_system_administrator()
    department = create_test_department(
        name="Listed Department",
    )

    try:
        response = client.get(
            "/api/v1/departments",
            headers=auth_headers(admin),
        )

        assert response.status_code == 200

        body = response.json()

        assert "items" in body
        assert "total" in body
        assert "offset" in body
        assert "limit" in body
        assert any(
            item["id"] == str(department.id)
            for item in body["items"]
        )

        for item in body["items"]:
            assert "id" in item
            assert "code" in item
            assert "name" in item
            assert "description" in item
            assert "is_active" in item
    finally:
        delete_test_user(admin.id)
        delete_test_department(department.id)


def test_system_administrator_can_search_departments():
    admin = create_system_administrator()
    department = create_test_department(
        name="Unique Department Search Target",
    )

    try:
        response = client.get(
            "/api/v1/departments",
            params={
                "search": "unique department search target",
            },
            headers=auth_headers(admin),
        )

        assert response.status_code == 200

        body = response.json()

        assert body["total"] >= 1
        assert any(
            item["id"] == str(department.id)
            for item in body["items"]
        )
    finally:
        delete_test_user(admin.id)
        delete_test_department(department.id)


def test_system_administrator_can_get_department():
    admin = create_system_administrator()
    department = create_test_department(
        name="Department Detail Target",
    )

    try:
        response = client.get(
            f"/api/v1/departments/{department.id}",
            headers=auth_headers(admin),
        )

        assert response.status_code == 200

        body = response.json()

        assert body["id"] == str(department.id)
        assert body["code"] == department.code
        assert body["name"] == "Department Detail Target"
        assert "password_hash" not in body
    finally:
        delete_test_user(admin.id)
        delete_test_department(department.id)


def test_unknown_department_returns_404():
    admin = create_system_administrator()

    try:
        response = client.get(
            f"/api/v1/departments/{uuid4()}",
            headers=auth_headers(admin),
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Department not found."
    finally:
        delete_test_user(admin.id)


def test_system_administrator_can_create_department():
    admin = create_system_administrator()
    department_id = None

    try:
        code = f"DPT-{uuid4().hex[:8].upper()}"

        response = client.post(
            "/api/v1/departments",
            headers=auth_headers(admin),
            json={
                "code": code,
                "name": "Created Department",
                "description": "Created department description",
            },
        )

        assert response.status_code == 201

        body = response.json()

        assert body["code"] == code
        assert body["name"] == "Created Department"
        assert body["description"] == "Created department description"
        assert body["is_active"] is True

        department_id = body["id"]
    finally:
        if department_id is not None:
            delete_test_department(department_id)

        delete_test_user(admin.id)


def test_duplicate_department_code_returns_409():
    admin = create_system_administrator()
    department = create_test_department(
        code=f"DPT-{uuid4().hex[:8].upper()}",
        name="Existing Department",
    )

    try:
        response = client.post(
            "/api/v1/departments",
            headers=auth_headers(admin),
            json={
                "code": department.code,
                "name": "Duplicate Department",
            },
        )

        assert response.status_code == 409
        assert (
            response.json()["detail"]
            == "A department with this code already exists."
        )
    finally:
        delete_test_user(admin.id)
        delete_test_department(department.id)


def test_invalid_department_request_returns_422():
    admin = create_system_administrator()

    try:
        response = client.post(
            "/api/v1/departments",
            headers=auth_headers(admin),
            json={
                "code": "A",
                "name": "A",
            },
        )

        assert response.status_code == 422
    finally:
        delete_test_user(admin.id)


def test_system_administrator_can_update_department():
    admin = create_system_administrator()
    department = create_test_department(
        name="Original Department",
    )

    try:
        new_code = f"DPT-{uuid4().hex[:8].upper()}"

        response = client.patch(
            f"/api/v1/departments/{department.id}",
            headers=auth_headers(admin),
            json={
                "code": new_code,
                "name": "Updated Department",
                "description": "Updated description",
            },
        )

        assert response.status_code == 200

        body = response.json()

        assert body["id"] == str(department.id)
        assert body["code"] == new_code
        assert body["name"] == "Updated Department"
        assert body["description"] == "Updated description"
    finally:
        delete_test_user(admin.id)
        delete_test_department(department.id)


def test_department_update_unknown_department_returns_404():
    admin = create_system_administrator()

    try:
        response = client.patch(
            f"/api/v1/departments/{uuid4()}",
            headers=auth_headers(admin),
            json={
                "code": f"DPT-{uuid4().hex[:8].upper()}",
                "name": "Unknown Department",
            },
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Department not found."
    finally:
        delete_test_user(admin.id)


def test_system_administrator_can_deactivate_department():
    admin = create_system_administrator()
    department = create_test_department(
        name="Deactivate Department",
    )

    try:
        response = client.patch(
            f"/api/v1/departments/{department.id}/status",
            headers=auth_headers(admin),
            json={
                "is_active": False,
            },
        )

        assert response.status_code == 200
        assert response.json()["is_active"] is False
    finally:
        delete_test_user(admin.id)
        delete_test_department(department.id)


def test_system_administrator_can_activate_department():
    admin = create_system_administrator()
    department = create_test_department(
        name="Activate Department",
    )

    db = SessionLocal()

    try:
        department.is_active = False
        db.commit()
    finally:
        db.close()

    try:
        response = client.patch(
            f"/api/v1/departments/{department.id}/status",
            headers=auth_headers(admin),
            json={
                "is_active": True,
            },
        )

        assert response.status_code == 200
        assert response.json()["is_active"] is True
    finally:
        delete_test_user(admin.id)
        delete_test_department(department.id)


def test_non_administrator_cannot_modify_department():
    user = create_test_user(
        full_name="Protected Department User",
    )
    department = create_test_department()

    try:
        response = client.patch(
            f"/api/v1/departments/{department.id}",
            headers=auth_headers(user),
            json={
                "code": department.code,
                "name": "Unauthorized Update",
            },
        )

        assert response.status_code == 403
    finally:
        delete_test_user(user.id)
        delete_test_department(department.id)

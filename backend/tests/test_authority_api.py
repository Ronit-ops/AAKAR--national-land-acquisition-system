from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.jwt import create_access_token
from app.db.session import SessionLocal
from app.main import app
from app.models.authority import Authority
from app.models.department import Department
from app.models.user import User
from app.services.auth_service import create_user
from app.services.authority_service import create_authority
from app.services.department_service import create_department
from app.services.rbac_service import assign_role


client = TestClient(app)

TEST_PASSWORD = "AAKAR-Authority-API-123!"


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
            or f"authority-api-{uuid4()}@example.com",
            password=TEST_PASSWORD,
            full_name=full_name,
        )
    finally:
        db.close()


def create_system_administrator() -> User:
    user = create_test_user(
        full_name="Authority API Administrator",
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
    name: str = "Test Department",
) -> Department:
    db = SessionLocal()

    try:
        return create_department(
            db=db,
            code=f"DPT-{uuid4().hex[:8].upper()}",
            name=name,
        )
    finally:
        db.close()


def create_test_authority(
    *,
    department_id,
    name: str = "Test Authority",
    authority_type: str = "STATE",
) -> Authority:
    db = SessionLocal()

    try:
        return create_authority(
            db=db,
            department_id=department_id,
            code=f"AUTH-{uuid4().hex[:8].upper()}",
            name=name,
            authority_type=authority_type,
        )
    finally:
        db.close()


def set_department_active_status(
    department_id,
    *,
    is_active: bool,
) -> None:
    db = SessionLocal()

    try:
        department = db.get(Department, department_id)

        if department is None:
            raise AssertionError("Test department not found.")

        department.is_active = is_active
        db.commit()
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


def test_authority_list_requires_authentication():
    response = client.get("/api/v1/authorities")

    assert response.status_code == 401


def test_authority_list_forbids_non_administrator():
    user = create_test_user(
        full_name="Regular Authority User",
    )

    try:
        response = client.get(
            "/api/v1/authorities",
            headers=auth_headers(user),
        )

        assert response.status_code == 403
    finally:
        delete_test_user(user.id)


def test_system_administrator_can_list_authorities():
    admin = create_system_administrator()
    department = create_test_department()
    authority = create_test_authority(
        department_id=department.id,
        name="Listed Authority",
    )

    try:
        response = client.get(
            "/api/v1/authorities",
            headers=auth_headers(admin),
        )

        assert response.status_code == 200

        body = response.json()

        assert "items" in body
        assert "total" in body
        assert "offset" in body
        assert "limit" in body

        assert any(
            item["id"] == str(authority.id)
            for item in body["items"]
        )
    finally:
        delete_test_user(admin.id)
        delete_test_authority(authority.id)
        delete_test_department(department.id)


def test_system_administrator_can_search_authorities():
    admin = create_system_administrator()
    department = create_test_department()
    authority = create_test_authority(
        department_id=department.id,
        name="Unique Authority Search Target",
    )

    try:
        response = client.get(
            "/api/v1/authorities",
            params={
                "search": "unique authority search target",
            },
            headers=auth_headers(admin),
        )

        assert response.status_code == 200

        body = response.json()

        assert body["total"] >= 1
        assert any(
            item["id"] == str(authority.id)
            for item in body["items"]
        )
    finally:
        delete_test_user(admin.id)
        delete_test_authority(authority.id)
        delete_test_department(department.id)


def test_system_administrator_can_filter_by_department():
    admin = create_system_administrator()
    first_department = create_test_department(
        name="First Authority Department",
    )
    second_department = create_test_department(
        name="Second Authority Department",
    )

    first_authority = create_test_authority(
        department_id=first_department.id,
        name="First Department Authority",
    )
    second_authority = create_test_authority(
        department_id=second_department.id,
        name="Second Department Authority",
    )

    try:
        response = client.get(
            "/api/v1/authorities",
            params={
                "department_id": str(first_department.id),
            },
            headers=auth_headers(admin),
        )

        assert response.status_code == 200

        body = response.json()

        authority_ids = {
            item["id"]
            for item in body["items"]
        }

        assert str(first_authority.id) in authority_ids
        assert str(second_authority.id) not in authority_ids
    finally:
        delete_test_user(admin.id)
        delete_test_authority(first_authority.id)
        delete_test_authority(second_authority.id)
        delete_test_department(first_department.id)
        delete_test_department(second_department.id)


def test_system_administrator_can_filter_by_authority_type():
    admin = create_system_administrator()
    department = create_test_department()

    central_authority = create_test_authority(
        department_id=department.id,
        name="Central Authority",
        authority_type="CENTRAL",
    )
    state_authority = create_test_authority(
        department_id=department.id,
        name="State Authority",
        authority_type="STATE",
    )

    try:
        response = client.get(
            "/api/v1/authorities",
            params={
                "authority_type": "state",
            },
            headers=auth_headers(admin),
        )

        assert response.status_code == 200

        body = response.json()

        authority_ids = {
            item["id"]
            for item in body["items"]
        }

        assert str(state_authority.id) in authority_ids
        assert str(central_authority.id) not in authority_ids
    finally:
        delete_test_user(admin.id)
        delete_test_authority(central_authority.id)
        delete_test_authority(state_authority.id)
        delete_test_department(department.id)


def test_invalid_authority_type_filter_returns_422():
    admin = create_system_administrator()

    try:
        response = client.get(
            "/api/v1/authorities",
            params={
                "authority_type": "INVALID",
            },
            headers=auth_headers(admin),
        )

        assert response.status_code == 422
        assert response.json()["detail"] == "Invalid authority type."
    finally:
        delete_test_user(admin.id)


def test_system_administrator_can_get_authority():
    admin = create_system_administrator()
    department = create_test_department()
    authority = create_test_authority(
        department_id=department.id,
        name="Authority Detail Target",
    )

    try:
        response = client.get(
            f"/api/v1/authorities/{authority.id}",
            headers=auth_headers(admin),
        )

        assert response.status_code == 200

        body = response.json()

        assert body["id"] == str(authority.id)
        assert body["department_id"] == str(department.id)
        assert body["code"] == authority.code
        assert body["name"] == "Authority Detail Target"
        assert body["authority_type"] == "STATE"
    finally:
        delete_test_user(admin.id)
        delete_test_authority(authority.id)
        delete_test_department(department.id)


def test_unknown_authority_returns_404():
    admin = create_system_administrator()

    try:
        response = client.get(
            f"/api/v1/authorities/{uuid4()}",
            headers=auth_headers(admin),
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Authority not found."
    finally:
        delete_test_user(admin.id)


def test_system_administrator_can_create_authority():
    admin = create_system_administrator()
    department = create_test_department()
    authority_id = None

    try:
        code = f"AUTH-{uuid4().hex[:8].upper()}"

        response = client.post(
            "/api/v1/authorities",
            headers=auth_headers(admin),
            json={
                "department_id": str(department.id),
                "code": code,
                "name": "Created Authority",
                "authority_type": "DISTRICT",
                "description": "Created authority description",
            },
        )

        assert response.status_code == 201

        body = response.json()

        assert body["code"] == code
        assert body["name"] == "Created Authority"
        assert body["authority_type"] == "DISTRICT"
        assert body["department_id"] == str(department.id)
        assert body["is_active"] is True

        authority_id = body["id"]
    finally:
        if authority_id is not None:
            delete_test_authority(authority_id)

        delete_test_user(admin.id)
        delete_test_department(department.id)


def test_create_authority_with_unknown_department_returns_404():
    admin = create_system_administrator()

    try:
        response = client.post(
            "/api/v1/authorities",
            headers=auth_headers(admin),
            json={
                "department_id": str(uuid4()),
                "code": f"AUTH-{uuid4().hex[:8].upper()}",
                "name": "Unknown Department Authority",
                "authority_type": "STATE",
            },
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Department not found."
    finally:
        delete_test_user(admin.id)


def test_duplicate_authority_code_returns_409():
    admin = create_system_administrator()
    department = create_test_department()
    authority = create_test_authority(
        department_id=department.id,
    )

    try:
        response = client.post(
            "/api/v1/authorities",
            headers=auth_headers(admin),
            json={
                "department_id": str(department.id),
                "code": authority.code,
                "name": "Duplicate Authority",
                "authority_type": "STATE",
            },
        )

        assert response.status_code == 409
        assert (
            response.json()["detail"]
            == "An authority with this code already exists."
        )
    finally:
        delete_test_user(admin.id)
        delete_test_authority(authority.id)
        delete_test_department(department.id)


def test_create_authority_with_inactive_department_returns_409():
    admin = create_system_administrator()
    department = create_test_department()
    authority_id = None

    try:
        set_department_active_status(
            department.id,
            is_active=False,
        )

        response = client.post(
            "/api/v1/authorities",
            headers=auth_headers(admin),
            json={
                "department_id": str(department.id),
                "code": f"AUTH-{uuid4().hex[:8].upper()}",
                "name": "Inactive Department Authority",
                "authority_type": "STATE",
            },
        )

        assert response.status_code == 409
        assert (
            response.json()["detail"]
            == "Cannot create an authority under an inactive department."
        )

        if response.status_code == 201:
            authority_id = response.json()["id"]
    finally:
        if authority_id is not None:
            delete_test_authority(authority_id)

        delete_test_user(admin.id)
        delete_test_department(department.id)


def test_invalid_authority_request_returns_422():
    admin = create_system_administrator()

    try:
        response = client.post(
            "/api/v1/authorities",
            headers=auth_headers(admin),
            json={
                "department_id": str(uuid4()),
                "code": "",
                "name": "A",
                "authority_type": "",
            },
        )

        assert response.status_code == 422
    finally:
        delete_test_user(admin.id)


def test_system_administrator_can_update_authority():
    admin = create_system_administrator()
    department = create_test_department()
    authority = create_test_authority(
        department_id=department.id,
        name="Original Authority",
    )

    try:
        new_code = f"AUTH-{uuid4().hex[:8].upper()}"

        response = client.patch(
            f"/api/v1/authorities/{authority.id}",
            headers=auth_headers(admin),
            json={
                "department_id": str(department.id),
                "code": new_code,
                "name": "Updated Authority",
                "authority_type": "DISTRICT",
                "description": "Updated description",
            },
        )

        assert response.status_code == 200

        body = response.json()

        assert body["id"] == str(authority.id)
        assert body["code"] == new_code
        assert body["name"] == "Updated Authority"
        assert body["authority_type"] == "DISTRICT"
        assert body["description"] == "Updated description"
    finally:
        delete_test_user(admin.id)
        delete_test_authority(authority.id)
        delete_test_department(department.id)


def test_update_authority_can_move_between_departments():
    admin = create_system_administrator()
    first_department = create_test_department(
        name="First Update Department",
    )
    second_department = create_test_department(
        name="Second Update Department",
    )
    authority = create_test_authority(
        department_id=first_department.id,
    )

    try:
        response = client.patch(
            f"/api/v1/authorities/{authority.id}",
            headers=auth_headers(admin),
            json={
                "department_id": str(second_department.id),
                "code": authority.code,
                "name": "Moved Authority",
                "authority_type": "STATE",
            },
        )

        assert response.status_code == 200
        assert response.json()["department_id"] == str(
            second_department.id
        )
    finally:
        delete_test_user(admin.id)
        delete_test_authority(authority.id)
        delete_test_department(first_department.id)
        delete_test_department(second_department.id)


def test_update_authority_unknown_authority_returns_404():
    admin = create_system_administrator()
    department = create_test_department()

    try:
        response = client.patch(
            f"/api/v1/authorities/{uuid4()}",
            headers=auth_headers(admin),
            json={
                "department_id": str(department.id),
                "code": f"AUTH-{uuid4().hex[:8].upper()}",
                "name": "Unknown Authority",
                "authority_type": "STATE",
            },
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Authority not found."
    finally:
        delete_test_user(admin.id)
        delete_test_department(department.id)


def test_update_authority_unknown_department_returns_404():
    admin = create_system_administrator()
    department = create_test_department()
    authority = create_test_authority(
        department_id=department.id,
    )

    try:
        response = client.patch(
            f"/api/v1/authorities/{authority.id}",
            headers=auth_headers(admin),
            json={
                "department_id": str(uuid4()),
                "code": authority.code,
                "name": "Updated Authority",
                "authority_type": "STATE",
            },
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Department not found."
    finally:
        delete_test_user(admin.id)
        delete_test_authority(authority.id)
        delete_test_department(department.id)


def test_update_authority_inactive_department_returns_409():
    admin = create_system_administrator()
    first_department = create_test_department(
        name="Active Source Department",
    )
    second_department = create_test_department(
        name="Inactive Target Department",
    )
    authority = create_test_authority(
        department_id=first_department.id,
    )

    try:
        set_department_active_status(
            second_department.id,
            is_active=False,
        )

        response = client.patch(
            f"/api/v1/authorities/{authority.id}",
            headers=auth_headers(admin),
            json={
                "department_id": str(second_department.id),
                "code": authority.code,
                "name": authority.name,
                "authority_type": authority.authority_type,
            },
        )

        assert response.status_code == 409
        assert (
            response.json()["detail"]
            == "Cannot assign an authority to an inactive department."
        )
    finally:
        delete_test_user(admin.id)
        delete_test_authority(authority.id)
        delete_test_department(first_department.id)
        delete_test_department(second_department.id)


def test_system_administrator_can_deactivate_authority():
    admin = create_system_administrator()
    department = create_test_department()
    authority = create_test_authority(
        department_id=department.id,
        name="Deactivate Authority",
    )

    try:
        response = client.patch(
            f"/api/v1/authorities/{authority.id}/status",
            headers=auth_headers(admin),
            json={
                "is_active": False,
            },
        )

        assert response.status_code == 200
        assert response.json()["is_active"] is False
    finally:
        delete_test_user(admin.id)
        delete_test_authority(authority.id)
        delete_test_department(department.id)


def test_system_administrator_can_activate_authority():
    admin = create_system_administrator()
    department = create_test_department()
    authority = create_test_authority(
        department_id=department.id,
        name="Activate Authority",
    )

    try:
        set_authority_active_status = False

        db = SessionLocal()

        try:
            persisted_authority = db.get(Authority, authority.id)

            if persisted_authority is None:
                raise AssertionError("Test authority not found.")

            persisted_authority.is_active = set_authority_active_status
            db.commit()
        finally:
            db.close()

        response = client.patch(
            f"/api/v1/authorities/{authority.id}/status",
            headers=auth_headers(admin),
            json={
                "is_active": True,
            },
        )

        assert response.status_code == 200
        assert response.json()["is_active"] is True
    finally:
        delete_test_user(admin.id)
        delete_test_authority(authority.id)
        delete_test_department(department.id)


def test_unknown_authority_status_target_returns_404():
    admin = create_system_administrator()

    try:
        response = client.patch(
            f"/api/v1/authorities/{uuid4()}/status",
            headers=auth_headers(admin),
            json={
                "is_active": False,
            },
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Authority not found."
    finally:
        delete_test_user(admin.id)


def test_non_administrator_cannot_modify_authority():
    user = create_test_user(
        full_name="Protected Authority User",
    )
    department = create_test_department()
    authority = create_test_authority(
        department_id=department.id,
    )

    try:
        response = client.patch(
            f"/api/v1/authorities/{authority.id}",
            headers=auth_headers(user),
            json={
                "department_id": str(department.id),
                "code": authority.code,
                "name": "Unauthorized Update",
                "authority_type": "STATE",
            },
        )

        assert response.status_code == 403
    finally:
        delete_test_user(user.id)
        delete_test_authority(authority.id)
        delete_test_department(department.id)

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.core.jwt import create_access_token
from app.db.session import SessionLocal
from app.main import app
from app.models.audit_event import AuditEvent
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.user import User
from app.services.auth_service import create_user
from app.services.permission_service import create_permission
from app.services.rbac_service import assign_role


client = TestClient(app)

TEST_PASSWORD = "AAKAR-Permission-API-123!"
TEST_PERMISSION_PREFIX = "test.permission.api"


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
            or f"permission-api-{uuid4()}@example.com",
            password=TEST_PASSWORD,
            full_name=full_name,
        )
    finally:
        db.close()


def create_system_administrator() -> User:
    user = create_test_user(
        full_name="Permission API Administrator",
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


def create_test_permission(
    *,
    code: str | None = None,
    name: str = "Test Permission",
    resource: str = "test",
    action: str = "read",
) -> Permission:
    db = SessionLocal()

    try:
        return create_permission(
            db=db,
            code=code or f"{TEST_PERMISSION_PREFIX}.{uuid4().hex}",
            name=name,
            resource=resource,
            action=action,
            description="Permission API test permission",
            is_system_permission=False,
        )
    finally:
        db.close()


def delete_test_user(user_id) -> None:
    db = SessionLocal()

    try:
        db.execute(
            delete(AuditEvent).where(
                AuditEvent.actor_user_id == user_id,
            )
        )

        user = db.get(User, user_id)

        if user is not None:
            db.delete(user)

        db.commit()
    finally:
        db.close()


def delete_test_permission(permission_id) -> None:
    db = SessionLocal()

    try:
        permission = db.get(Permission, permission_id)

        if permission is not None:
            db.delete(permission)

        db.commit()
    finally:
        db.close()


def cleanup_test_permissions() -> None:
    db = SessionLocal()

    try:
        db.execute(
            delete(Permission).where(
                Permission.code.like(
                    f"{TEST_PERMISSION_PREFIX}.%"
                )
            )
        )

        db.commit()
    finally:
        db.close()


def auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(user.id)

    return {
        "Authorization": f"Bearer {token}",
    }


def test_permission_list_requires_authentication():
    response = client.get("/api/v1/permissions")

    assert response.status_code == 401


def test_permission_list_forbids_non_administrator():
    user = create_test_user(
        full_name="Regular Permission User",
    )

    try:
        response = client.get(
            "/api/v1/permissions",
            headers=auth_headers(user),
        )

        assert response.status_code == 403
    finally:
        delete_test_user(user.id)


def test_system_administrator_can_list_permissions():
    admin = create_system_administrator()
    permission = create_test_permission(
        name="List Target Permission",
    )

    try:
        response = client.get(
            "/api/v1/permissions",
            headers=auth_headers(admin),
        )

        assert response.status_code == 200

        body = response.json()

        assert "items" in body
        assert "total" in body
        assert "offset" in body
        assert "limit" in body

        assert any(
            item["id"] == str(permission.id)
            for item in body["items"]
        )

        for item in body["items"]:
            assert "id" in item
            assert "code" in item
            assert "name" in item
            assert "resource" in item
            assert "action" in item
            assert "description" in item
            assert "is_system_permission" in item
            assert "is_active" in item
    finally:
        delete_test_user(admin.id)
        delete_test_permission(permission.id)


def test_system_administrator_can_search_permissions():
    admin = create_system_administrator()
    permission = create_test_permission(
        name="Unique Permission Search Target",
    )

    try:
        response = client.get(
            "/api/v1/permissions",
            params={
                "search": "unique permission search target",
            },
            headers=auth_headers(admin),
        )

        assert response.status_code == 200

        body = response.json()

        assert body["total"] >= 1
        assert any(
            item["id"] == str(permission.id)
            for item in body["items"]
        )
    finally:
        delete_test_user(admin.id)
        delete_test_permission(permission.id)


def test_system_administrator_can_filter_permissions():
    admin = create_system_administrator()

    permission = create_test_permission(
        resource="filter-resource",
        action="filter-action",
    )

    try:
        response = client.get(
            "/api/v1/permissions",
            params={
                "resource": "filter-resource",
                "action": "filter-action",
            },
            headers=auth_headers(admin),
        )

        assert response.status_code == 200

        body = response.json()

        assert body["total"] >= 1
        assert any(
            item["id"] == str(permission.id)
            for item in body["items"]
        )
    finally:
        delete_test_user(admin.id)
        delete_test_permission(permission.id)


def test_system_administrator_can_get_permission():
    admin = create_system_administrator()
    permission = create_test_permission(
        name="Permission Detail Target",
    )

    try:
        response = client.get(
            f"/api/v1/permissions/{permission.id}",
            headers=auth_headers(admin),
        )

        assert response.status_code == 200

        body = response.json()

        assert body["id"] == str(permission.id)
        assert body["code"] == permission.code
        assert body["name"] == "Permission Detail Target"
        assert "password_hash" not in body
    finally:
        delete_test_user(admin.id)
        delete_test_permission(permission.id)


def test_unknown_permission_returns_404():
    admin = create_system_administrator()

    try:
        response = client.get(
            f"/api/v1/permissions/{uuid4()}",
            headers=auth_headers(admin),
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Permission not found."
    finally:
        delete_test_user(admin.id)


def test_system_administrator_can_create_permission():
    admin = create_system_administrator()
    permission_id = None

    try:
        code = f"{TEST_PERMISSION_PREFIX}.{uuid4().hex}"

        response = client.post(
            "/api/v1/permissions",
            headers=auth_headers(admin),
            json={
                "code": code,
                "name": "Created Permission",
                "resource": "test",
                "action": "create",
                "description": "Created permission description",
            },
        )

        assert response.status_code == 201

        body = response.json()

        assert body["code"] == code
        assert body["name"] == "Created Permission"
        assert body["resource"] == "test"
        assert body["action"] == "create"
        assert body["description"] == "Created permission description"
        assert body["is_system_permission"] is True
        assert body["is_active"] is True

        permission_id = body["id"]
    finally:
        if permission_id is not None:
            delete_test_permission(permission_id)

        delete_test_user(admin.id)


def test_permission_creation_normalizes_values():
    admin = create_system_administrator()
    permission_id = None

    try:
        code = f"{TEST_PERMISSION_PREFIX}.{uuid4().hex}"

        response = client.post(
            "/api/v1/permissions",
            headers=auth_headers(admin),
            json={
                "code": f"  {code.upper()}  ",
                "name": "  Normalized Permission  ",
                "resource": "  TEST  ",
                "action": "  CREATE  ",
                "description": "  Normalized description  ",
            },
        )

        assert response.status_code == 201

        body = response.json()

        assert body["code"] == code
        assert body["name"] == "Normalized Permission"
        assert body["resource"] == "test"
        assert body["action"] == "create"
        assert body["description"] == "Normalized description"

        permission_id = body["id"]
    finally:
        if permission_id is not None:
            delete_test_permission(permission_id)

        delete_test_user(admin.id)


def test_duplicate_permission_code_returns_409():
    admin = create_system_administrator()
    permission = create_test_permission()

    try:
        response = client.post(
            "/api/v1/permissions",
            headers=auth_headers(admin),
            json={
                "code": permission.code,
                "name": "Duplicate Permission",
                "resource": "duplicate",
                "action": "create",
            },
        )

        assert response.status_code == 409
        assert (
            response.json()["detail"]
            == "A permission with this code already exists."
        )
    finally:
        delete_test_user(admin.id)
        delete_test_permission(permission.id)


def test_invalid_permission_request_returns_422():
    admin = create_system_administrator()

    try:
        response = client.post(
            "/api/v1/permissions",
            headers=auth_headers(admin),
            json={
                "code": "",
                "name": "",
                "resource": "",
                "action": "",
            },
        )

        assert response.status_code == 422
    finally:
        delete_test_user(admin.id)


def test_system_administrator_can_update_permission():
    admin = create_system_administrator()
    permission = create_test_permission(
        name="Original Permission",
    )

    try:
        new_code = f"{TEST_PERMISSION_PREFIX}.{uuid4().hex}"

        response = client.patch(
            f"/api/v1/permissions/{permission.id}",
            headers=auth_headers(admin),
            json={
                "code": new_code,
                "name": "Updated Permission",
                "resource": "updated",
                "action": "write",
                "description": "Updated description",
            },
        )

        assert response.status_code == 200

        body = response.json()

        assert body["id"] == str(permission.id)
        assert body["code"] == new_code
        assert body["name"] == "Updated Permission"
        assert body["resource"] == "updated"
        assert body["action"] == "write"
        assert body["description"] == "Updated description"
    finally:
        delete_test_user(admin.id)
        delete_test_permission(permission.id)


def test_permission_update_unknown_permission_returns_404():
    admin = create_system_administrator()

    try:
        response = client.patch(
            f"/api/v1/permissions/{uuid4()}",
            headers=auth_headers(admin),
            json={
                "code": f"{TEST_PERMISSION_PREFIX}.{uuid4().hex}",
                "name": "Unknown Permission",
                "resource": "unknown",
                "action": "update",
            },
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Permission not found."
    finally:
        delete_test_user(admin.id)


def test_permission_update_duplicate_code_returns_409():
    admin = create_system_administrator()
    first = create_test_permission()
    second = create_test_permission()

    try:
        response = client.patch(
            f"/api/v1/permissions/{second.id}",
            headers=auth_headers(admin),
            json={
                "code": first.code,
                "name": "Updated Permission",
                "resource": "updated",
                "action": "write",
            },
        )

        assert response.status_code == 409
        assert (
            response.json()["detail"]
            == "A permission with this code already exists."
        )
    finally:
        delete_test_user(admin.id)
        delete_test_permission(first.id)
        delete_test_permission(second.id)


def test_system_administrator_can_deactivate_permission():
    admin = create_system_administrator()
    permission = create_test_permission(
        name="Deactivate Permission",
    )

    try:
        response = client.patch(
            f"/api/v1/permissions/{permission.id}/status",
            headers=auth_headers(admin),
            json={
                "is_active": False,
            },
        )

        assert response.status_code == 200
        assert response.json()["is_active"] is False
    finally:
        delete_test_user(admin.id)
        delete_test_permission(permission.id)


def test_system_administrator_can_activate_permission():
    admin = create_system_administrator()
    permission = create_test_permission(
        name="Activate Permission",
    )

    db = SessionLocal()

    try:
        db_permission = db.scalar(
            select(Permission).where(Permission.id == permission.id)
        )

        assert db_permission is not None

        db_permission.is_active = False
        db.commit()
    finally:
        db.close()

    try:
        response = client.patch(
            f"/api/v1/permissions/{permission.id}/status",
            headers=auth_headers(admin),
            json={
                "is_active": True,
            },
        )

        assert response.status_code == 200
        assert response.json()["is_active"] is True
    finally:
        delete_test_user(admin.id)
        delete_test_permission(permission.id)


def test_non_administrator_cannot_modify_permission():
    user = create_test_user(
        full_name="Protected Permission User",
    )
    permission = create_test_permission()

    try:
        response = client.patch(
            f"/api/v1/permissions/{permission.id}",
            headers=auth_headers(user),
            json={
                "code": permission.code,
                "name": "Unauthorized Update",
                "resource": "test",
                "action": "write",
            },
        )

        assert response.status_code == 403
    finally:
        delete_test_user(user.id)
        delete_test_permission(permission.id)


def test_system_administrator_can_assign_permission_to_role():
    admin = create_system_administrator()
    permission = create_test_permission(
        name="Role Assignment Permission",
    )

    try:
        response = client.post(
            "/api/v1/permissions/roles/district_collector/assign",
            headers=auth_headers(admin),
            json={
                "permission_code": permission.code,
            },
        )

        assert response.status_code == 200

        body = response.json()

        assert body["role_code"] == "district_collector"
        assert body["permission_code"] == permission.code
        assert body["permission_id"] == str(permission.id)
        assert "assigned_at" in body
    finally:
        db = SessionLocal()

        try:
            db.execute(
                delete(RolePermission).where(
                    RolePermission.permission_id == permission.id,
                )
            )
            db.commit()
        finally:
            db.close()

        delete_test_user(admin.id)
        delete_test_permission(permission.id)


def test_assigning_same_permission_twice_is_idempotent():
    admin = create_system_administrator()
    permission = create_test_permission(
        name="Idempotent Permission",
    )

    try:
        first_response = client.post(
            "/api/v1/permissions/roles/district_collector/assign",
            headers=auth_headers(admin),
            json={
                "permission_code": permission.code,
            },
        )

        second_response = client.post(
            "/api/v1/permissions/roles/district_collector/assign",
            headers=auth_headers(admin),
            json={
                "permission_code": permission.code,
            },
        )

        assert first_response.status_code == 200
        assert second_response.status_code == 200

        first_body = first_response.json()
        second_body = second_response.json()

        assert (
            first_body["permission_id"]
            == second_body["permission_id"]
        )
        assert (
            first_body["role_id"]
            == second_body["role_id"]
        )
        assert (
            first_body["assigned_at"]
            == second_body["assigned_at"]
        )
    finally:
        db = SessionLocal()

        try:
            db.execute(
                delete(RolePermission).where(
                    RolePermission.permission_id == permission.id,
                )
            )
            db.commit()
        finally:
            db.close()

        delete_test_user(admin.id)
        delete_test_permission(permission.id)


def test_assigning_unknown_role_returns_404():
    admin = create_system_administrator()
    permission = create_test_permission()

    try:
        response = client.post(
            "/api/v1/permissions/roles/does_not_exist/assign",
            headers=auth_headers(admin),
            json={
                "permission_code": permission.code,
            },
        )

        assert response.status_code == 404
        assert (
            response.json()["detail"]
            == "Active role not found."
        )
    finally:
        delete_test_user(admin.id)
        delete_test_permission(permission.id)


def test_assigning_unknown_permission_returns_404():
    admin = create_system_administrator()

    try:
        response = client.post(
            "/api/v1/permissions/roles/district_collector/assign",
            headers=auth_headers(admin),
            json={
                "permission_code": (
                    f"{TEST_PERMISSION_PREFIX}.does-not-exist"
                ),
            },
        )

        assert response.status_code == 404
        assert (
            response.json()["detail"]
            == "Active permission not found."
        )
    finally:
        delete_test_user(admin.id)


def test_assigning_inactive_permission_returns_404():
    admin = create_system_administrator()
    permission = create_test_permission(
        name="Inactive Assignment Permission",
    )

    db = SessionLocal()

    try:
        db_permission = db.scalar(
            select(Permission).where(Permission.id == permission.id)
        )

        assert db_permission is not None

        db_permission.is_active = False
        db.commit()
    finally:
        db.close()

    try:
        response = client.post(
            "/api/v1/permissions/roles/district_collector/assign",
            headers=auth_headers(admin),
            json={
                "permission_code": permission.code,
            },
        )

        assert response.status_code == 404
        assert (
            response.json()["detail"]
            == "Active permission not found."
        )
    finally:
        delete_test_user(admin.id)
        delete_test_permission(permission.id)


def test_non_administrator_cannot_assign_permission():
    user = create_test_user(
        full_name="Protected Permission Assignment User",
    )
    permission = create_test_permission()

    try:
        response = client.post(
            "/api/v1/permissions/roles/district_collector/assign",
            headers=auth_headers(user),
            json={
                "permission_code": permission.code,
            },
        )

        assert response.status_code == 403
    finally:
        delete_test_user(user.id)
        delete_test_permission(permission.id)


def test_system_administrator_can_remove_role_permission():
    admin = create_system_administrator()
    permission = create_test_permission(
        name="Role Removal Permission",
    )

    db = SessionLocal()

    try:
        role = db.scalar(
            select(Role).where(
                Role.code == "district_collector",
            )
        )

        assert role is not None

        db.add(
            RolePermission(
                role_id=role.id,
                permission_id=permission.id,
            )
        )
        db.commit()
    finally:
        db.close()

    try:
        response = client.delete(
            "/api/v1/permissions/roles/"
            f"district_collector/assign/{permission.code}",
            headers=auth_headers(admin),
        )

        assert response.status_code == 204
    finally:
        delete_test_user(admin.id)
        delete_test_permission(permission.id)


def test_removing_missing_role_permission_returns_404():
    admin = create_system_administrator()
    permission = create_test_permission()

    try:
        response = client.delete(
            "/api/v1/permissions/roles/"
            f"district_collector/assign/{permission.code}",
            headers=auth_headers(admin),
        )

        assert response.status_code == 404
        assert (
            response.json()["detail"]
            == "Role permission assignment not found."
        )
    finally:
        delete_test_user(admin.id)
        delete_test_permission(permission.id)


def test_non_administrator_cannot_remove_role_permission():
    user = create_test_user(
        full_name="Protected Permission Removal User",
    )
    permission = create_test_permission()

    try:
        response = client.delete(
            "/api/v1/permissions/roles/"
            f"district_collector/assign/{permission.code}",
            headers=auth_headers(user),
        )

        assert response.status_code == 403
    finally:
        delete_test_user(user.id)
        delete_test_permission(permission.id)


def test_permission_creation_records_audit_event():
    admin = create_system_administrator()
    permission_id = None

    try:
        code = f"{TEST_PERMISSION_PREFIX}.{uuid4().hex}"

        response = client.post(
            "/api/v1/permissions",
            headers=auth_headers(admin),
            json={
                "code": code,
                "name": "Audited Permission",
                "resource": "audit",
                "action": "create",
            },
        )

        assert response.status_code == 201

        permission_id = response.json()["id"]

        db = SessionLocal()

        try:
            event = db.scalar(
                select(AuditEvent)
                .where(
                    AuditEvent.actor_user_id == admin.id,
                    AuditEvent.action == "permission_created",
                    AuditEvent.entity_type == "permission",
                    AuditEvent.entity_id == permission_id,
                )
                .order_by(AuditEvent.created_at.desc())
            )

            assert event is not None
            assert event.result == "success"
        finally:
            db.close()
    finally:
        if permission_id is not None:
            delete_test_permission(permission_id)

        delete_test_user(admin.id)


def test_permission_status_change_records_audit_event():
    admin = create_system_administrator()
    permission = create_test_permission(
        name="Audited Status Permission",
    )

    try:
        response = client.patch(
            f"/api/v1/permissions/{permission.id}/status",
            headers=auth_headers(admin),
            json={
                "is_active": False,
            },
        )

        assert response.status_code == 200

        db = SessionLocal()

        try:
            event = db.scalar(
                select(AuditEvent)
                .where(
                    AuditEvent.actor_user_id == admin.id,
                    AuditEvent.action
                    == "permission_status_changed",
                    AuditEvent.entity_type == "permission",
                    AuditEvent.entity_id == permission.id,
                )
                .order_by(AuditEvent.created_at.desc())
            )

            assert event is not None
            assert event.result == "success"
        finally:
            db.close()
    finally:
        delete_test_user(admin.id)
        delete_test_permission(permission.id)


def test_role_permission_assignment_records_audit_event():
    admin = create_system_administrator()
    permission = create_test_permission(
        name="Audited Assignment Permission",
    )

    try:
        response = client.post(
            "/api/v1/permissions/roles/district_collector/assign",
            headers=auth_headers(admin),
            json={
                "permission_code": permission.code,
            },
        )

        assert response.status_code == 200

        db = SessionLocal()

        try:
            event = db.scalar(
                select(AuditEvent)
                .where(
                    AuditEvent.actor_user_id == admin.id,
                    AuditEvent.action
                    == "role_permission_assigned",
                    AuditEvent.entity_type == "role_permission",
                )
                .order_by(AuditEvent.created_at.desc())
            )

            assert event is not None
            assert event.result == "success"
            assert (
                event.details["role_code"]
                == "district_collector"
            )
            assert (
                event.details["permission_code"]
                == permission.code
            )
        finally:
            db.close()
    finally:
        db = SessionLocal()

        try:
            db.execute(
                delete(RolePermission).where(
                    RolePermission.permission_id == permission.id,
                )
            )
            db.commit()
        finally:
            db.close()

        delete_test_user(admin.id)
        delete_test_permission(permission.id)


def test_role_permission_removal_records_audit_event():
    admin = create_system_administrator()
    permission = create_test_permission(
        name="Audited Removal Permission",
    )

    db = SessionLocal()

    try:
        role = db.scalar(
            select(Role).where(
                Role.code == "district_collector",
            )
        )

        assert role is not None

        db.add(
            RolePermission(
                role_id=role.id,
                permission_id=permission.id,
            )
        )
        db.commit()
    finally:
        db.close()

    try:
        response = client.delete(
            "/api/v1/permissions/roles/"
            f"district_collector/assign/{permission.code}",
            headers=auth_headers(admin),
        )

        assert response.status_code == 204

        db = SessionLocal()

        try:
            event = db.scalar(
                select(AuditEvent)
                .where(
                    AuditEvent.actor_user_id == admin.id,
                    AuditEvent.action
                    == "role_permission_removed",
                    AuditEvent.entity_type == "role_permission",
                    AuditEvent.entity_id == permission.id,
                )
                .order_by(AuditEvent.created_at.desc())
            )

            assert event is not None
            assert event.result == "success"
            assert (
                event.details["role_code"]
                == "district_collector"
            )
            assert (
                event.details["permission_code"]
                == permission.code
            )
        finally:
            db.close()
    finally:
        delete_test_user(admin.id)
        delete_test_permission(permission.id)
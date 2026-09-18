from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.core.jwt import create_access_token
from app.db.session import SessionLocal
from app.main import app
from app.models.audit_event import AuditEvent
from app.models.user import User
from app.services.auth_service import create_user
from app.services.rbac_service import assign_role


client = TestClient(app)

TEST_PASSWORD = "AAKAR-User-Audit-123!"


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
            or f"user-audit-api-{uuid4()}@example.com",
            password=TEST_PASSWORD,
            full_name=full_name,
        )
    finally:
        db.close()


def create_system_administrator() -> User:
    user = create_test_user(
        full_name="User Audit Administrator",
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


def auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(user.id)

    return {
        "Authorization": f"Bearer {token}",
    }


def delete_test_user(user_id) -> None:
    db = SessionLocal()

    try:
        db.execute(
            delete(AuditEvent).where(
                AuditEvent.actor_user_id == user_id
            )
        )

        db.execute(
            delete(AuditEvent).where(
                AuditEvent.entity_id == user_id
            )
        )

        user = db.get(User, user_id)

        if user is not None:
            db.delete(user)

        db.commit()
    finally:
        db.close()


def test_create_user_records_audit_event():
    admin = create_system_administrator()
    created_user_id = None

    try:
        email = f"audit-created-{uuid4()}@example.com"

        response = client.post(
            "/api/v1/users",
            headers=auth_headers(admin),
            json={
                "email": email,
                "password": TEST_PASSWORD,
                "full_name": "Audited Created User",
            },
        )

        assert response.status_code == 201

        created_user_id = response.json()["id"]

        db = SessionLocal()

        try:
            event = db.scalar(
                select(AuditEvent).where(
                    AuditEvent.actor_user_id == admin.id,
                    AuditEvent.entity_id == created_user_id,
                    AuditEvent.action == "user_created",
                )
            )

            assert event is not None
            assert event.entity_type == "user"
            assert event.result == "success"
            assert event.details is not None
            assert event.details["email"] == email
            assert event.details["full_name"] == "Audited Created User"
            assert "password" not in event.details
            assert "password_hash" not in event.details
        finally:
            db.close()
    finally:
        if created_user_id is not None:
            delete_test_user(created_user_id)

        delete_test_user(admin.id)


def test_update_user_records_audit_event():
    admin = create_system_administrator()
    target = create_test_user(
        full_name="Audit Update Target",
    )

    try:
        response = client.patch(
            f"/api/v1/users/{target.id}",
            headers=auth_headers(admin),
            json={
                "email": f"audit-updated-{uuid4()}@example.com",
                "full_name": "Audited Updated User",
            },
        )

        assert response.status_code == 200

        db = SessionLocal()

        try:
            event = db.scalar(
                select(AuditEvent).where(
                    AuditEvent.actor_user_id == admin.id,
                    AuditEvent.entity_id == target.id,
                    AuditEvent.action == "user_profile_updated",
                )
            )

            assert event is not None
            assert event.entity_type == "user"
            assert event.result == "success"
            assert event.details == {
                "fields": [
                    "full_name",
                    "email",
                ],
            }
        finally:
            db.close()
    finally:
        delete_test_user(admin.id)
        delete_test_user(target.id)


def test_status_change_records_audit_event():
    admin = create_system_administrator()
    target = create_test_user(
        full_name="Audit Status Target",
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

        db = SessionLocal()

        try:
            event = db.scalar(
                select(AuditEvent).where(
                    AuditEvent.actor_user_id == admin.id,
                    AuditEvent.entity_id == target.id,
                    AuditEvent.action == "user_status_changed",
                )
            )

            assert event is not None
            assert event.entity_type == "user"
            assert event.result == "success"
            assert event.details == {
                "is_active": False,
            }
        finally:
            db.close()
    finally:
        delete_test_user(admin.id)
        delete_test_user(target.id)

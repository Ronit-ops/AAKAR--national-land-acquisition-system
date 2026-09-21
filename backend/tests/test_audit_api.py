from datetime import datetime, timedelta, timezone
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
from app.services.rbac_service import assign_role


client = TestClient(app)

TEST_PASSWORD = "AAKAR-Audit-API-123!"


def create_test_user(
    *,
    full_name: str,
    email: str | None = None,
) -> User:
    db = SessionLocal()

    try:
        return create_user(
            db=db,
            email=email or f"audit-api-{uuid4()}@example.com",
            password=TEST_PASSWORD,
            full_name=full_name,
        )
    finally:
        db.close()


def assign_role_to_user(
    *,
    user_id,
    role_code: str,
) -> None:
    db = SessionLocal()

    try:
        assign_role(
            db=db,
            user_id=user_id,
            role_code=role_code,
        )
    finally:
        db.close()


def auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(user.id)

    return {
        "Authorization": f"Bearer {token}",
    }


def create_audit_event(
    *,
    actor_user_id,
    action: str = "test.audit.read",
    entity_type: str = "test_entity",
    entity_id=None,
    result: str = "success",
    details: dict[str, object] | None = None,
    created_at: datetime | None = None,
) -> AuditEvent:
    db = SessionLocal()

    try:
        event = AuditEvent(
            actor_user_id=actor_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            result=result,
            details=details,
        )

        if created_at is not None:
            event.created_at = created_at

        db.add(event)
        db.commit()
        db.refresh(event)

        return event
    finally:
        db.close()


def delete_test_audit_events(event_ids: list) -> None:
    if not event_ids:
        return

    db = SessionLocal()

    try:
        db.execute(
            delete(AuditEvent).where(
                AuditEvent.id.in_(event_ids)
            )
        )
        db.commit()
    finally:
        db.close()


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


def test_audit_list_requires_authentication():
    response = client.get("/api/v1/audit")

    assert response.status_code == 401


def test_audit_list_forbids_user_without_audit_permission():
    user = create_test_user(
        full_name="Audit Unauthorized User",
    )

    try:
        response = client.get(
            "/api/v1/audit",
            headers=auth_headers(user),
        )

        assert response.status_code == 403
    finally:
        delete_test_user(user.id)


def test_audit_list_allows_user_with_audit_permission():
    user = create_test_user(
        full_name="Audit Authorized User",
    )

    assign_role_to_user(
        user_id=user.id,
        role_code="audit_compliance",
    )

    event_id = None

    try:
        event = create_audit_event(
            actor_user_id=user.id,
            action="audit.test.allowed",
            entity_type="test_entity",
            details={"source": "audit-api-test"},
        )

        event_id = event.id

        response = client.get(
            "/api/v1/audit",
            headers=auth_headers(user),
        )

        assert response.status_code == 200

        body = response.json()

        assert "items" in body
        assert "total" in body
        assert "offset" in body
        assert "limit" in body

        assert any(
            item["id"] == str(event.id)
            for item in body["items"]
        )
    finally:
        delete_test_audit_events([event_id] if event_id else [])
        delete_test_user(user.id)


def test_audit_list_returns_expected_event_fields():
    user = create_test_user(
        full_name="Audit Field Test User",
    )

    assign_role_to_user(
        user_id=user.id,
        role_code="audit_compliance",
    )

    event = create_audit_event(
        actor_user_id=user.id,
        action="audit.test.fields",
        entity_type="test_entity",
        entity_id=uuid4(),
        result="success",
        details={
            "field": "value",
            "count": 2,
        },
    )

    try:
        response = client.get(
            "/api/v1/audit",
            params={
                "entity_id": str(event.entity_id),
            },
            headers=auth_headers(user),
        )

        assert response.status_code == 200

        body = response.json()

        assert body["total"] == 1
        assert len(body["items"]) == 1

        item = body["items"][0]

        assert item["id"] == str(event.id)
        assert item["actor_user_id"] == str(user.id)
        assert item["action"] == "audit.test.fields"
        assert item["entity_type"] == "test_entity"
        assert item["entity_id"] == str(event.entity_id)
        assert item["result"] == "success"
        assert item["details"] == {
            "field": "value",
            "count": 2,
        }
        assert "created_at" in item
    finally:
        delete_test_audit_events([event.id])
        delete_test_user(user.id)


def test_audit_list_supports_search():
    user = create_test_user(
        full_name="Audit Search User",
    )

    assign_role_to_user(
        user_id=user.id,
        role_code="audit_compliance",
    )

    matching = create_audit_event(
        actor_user_id=user.id,
        action="unique.audit.search.target",
        entity_type="search_entity",
    )

    non_matching = create_audit_event(
        actor_user_id=user.id,
        action="different.audit.event",
        entity_type="other_entity",
    )

    try:
        response = client.get(
            "/api/v1/audit",
            params={
                "search": "unique.audit.search.target",
            },
            headers=auth_headers(user),
        )

        assert response.status_code == 200

        body = response.json()

        assert body["total"] == 1
        assert body["items"][0]["id"] == str(matching.id)
        assert body["items"][0]["id"] != str(non_matching.id)
    finally:
        delete_test_audit_events(
            [
                matching.id,
                non_matching.id,
            ]
        )
        delete_test_user(user.id)


def test_audit_list_supports_action_entity_and_result_filters():
    user = create_test_user(
        full_name="Audit Filter User",
    )

    assign_role_to_user(
        user_id=user.id,
        role_code="audit_compliance",
    )

    target_entity_id = uuid4()

    matching = create_audit_event(
        actor_user_id=user.id,
        action="filter.target",
        entity_type="filter_entity",
        entity_id=target_entity_id,
        result="success",
    )

    wrong_action = create_audit_event(
        actor_user_id=user.id,
        action="filter.other",
        entity_type="filter_entity",
        entity_id=target_entity_id,
        result="success",
    )

    wrong_result = create_audit_event(
        actor_user_id=user.id,
        action="filter.target",
        entity_type="filter_entity",
        entity_id=target_entity_id,
        result="failure",
    )

    try:
        response = client.get(
            "/api/v1/audit",
            params={
                "action": "FILTER.TARGET",
                "entity_type": "FILTER_ENTITY",
                "result": "SUCCESS",
            },
            headers=auth_headers(user),
        )

        assert response.status_code == 200

        body = response.json()

        assert body["total"] == 1
        assert body["items"][0]["id"] == str(matching.id)
        assert body["items"][0]["id"] != str(wrong_action.id)
        assert body["items"][0]["id"] != str(wrong_result.id)
    finally:
        delete_test_audit_events(
            [
                matching.id,
                wrong_action.id,
                wrong_result.id,
            ]
        )
        delete_test_user(user.id)


def test_audit_list_supports_actor_filter():
    user = create_test_user(
        full_name="Audit Actor User",
    )

    other_user = create_test_user(
        full_name="Audit Other Actor User",
    )

    assign_role_to_user(
        user_id=user.id,
        role_code="audit_compliance",
    )

    event_for_user = create_audit_event(
        actor_user_id=user.id,
        action="actor.target",
        entity_type="actor_entity",
    )

    event_for_other_user = create_audit_event(
        actor_user_id=other_user.id,
        action="actor.other",
        entity_type="actor_entity",
    )

    try:
        response = client.get(
            "/api/v1/audit",
            params={
                "actor_user_id": str(user.id),
            },
            headers=auth_headers(user),
        )

        assert response.status_code == 200

        body = response.json()

        assert body["total"] == 1
        assert body["items"][0]["id"] == str(event_for_user.id)
        assert body["items"][0]["id"] != str(event_for_other_user.id)
    finally:
        delete_test_audit_events(
            [
                event_for_user.id,
                event_for_other_user.id,
            ]
        )
        delete_test_user(user.id)
        delete_test_user(other_user.id)


def test_audit_list_supports_date_range():
    user = create_test_user(
        full_name="Audit Date User",
    )

    assign_role_to_user(
        user_id=user.id,
        role_code="audit_compliance",
    )

    now = datetime.now(timezone.utc)

    old_event = create_audit_event(
        actor_user_id=user.id,
        action="date.old",
        entity_type="date_entity",
        created_at=now - timedelta(days=2),
    )

    current_event = create_audit_event(
        actor_user_id=user.id,
        action="date.current",
        entity_type="date_entity",
        created_at=now,
    )

    try:
        start_at = (now - timedelta(hours=1)).isoformat()
        end_at = (now + timedelta(hours=1)).isoformat()

        response = client.get(
            "/api/v1/audit",
            params={
                "actor_user_id": str(user.id),
                "start_at": start_at,
                "end_at": end_at,
            },
            headers=auth_headers(user),
        )

        assert response.status_code == 200

        body = response.json()

        assert body["total"] == 1
        assert body["items"][0]["id"] == str(current_event.id)
        assert body["items"][0]["id"] != str(old_event.id)
    finally:
        delete_test_audit_events(
            [
                old_event.id,
                current_event.id,
            ]
        )
        delete_test_user(user.id)


def test_audit_list_supports_pagination_and_newest_first():
    user = create_test_user(
        full_name="Audit Pagination User",
    )

    assign_role_to_user(
        user_id=user.id,
        role_code="audit_compliance",
    )

    now = datetime.now(timezone.utc)

    older_event = create_audit_event(
        actor_user_id=user.id,
        action="pagination.old",
        entity_type="pagination_entity",
        created_at=now - timedelta(minutes=2),
    )

    newer_event = create_audit_event(
        actor_user_id=user.id,
        action="pagination.new",
        entity_type="pagination_entity",
        created_at=now,
    )

    try:
        response = client.get(
            "/api/v1/audit",
            params={
                "entity_type": "pagination_entity",
                "offset": 0,
                "limit": 1,
            },
            headers=auth_headers(user),
        )

        assert response.status_code == 200

        body = response.json()

        assert body["total"] == 2
        assert body["offset"] == 0
        assert body["limit"] == 1
        assert len(body["items"]) == 1
        assert body["items"][0]["id"] == str(newer_event.id)

        response = client.get(
            "/api/v1/audit",
            params={
                "entity_type": "pagination_entity",
                "offset": 1,
                "limit": 1,
            },
            headers=auth_headers(user),
        )

        assert response.status_code == 200

        body = response.json()

        assert body["total"] == 2
        assert body["offset"] == 1
        assert body["limit"] == 1
        assert len(body["items"]) == 1
        assert body["items"][0]["id"] == str(older_event.id)
    finally:
        delete_test_audit_events(
            [
                older_event.id,
                newer_event.id,
            ]
        )
        delete_test_user(user.id)


def test_audit_detail_returns_event():
    user = create_test_user(
        full_name="Audit Detail User",
    )

    assign_role_to_user(
        user_id=user.id,
        role_code="audit_compliance",
    )

    event = create_audit_event(
        actor_user_id=user.id,
        action="detail.target",
        entity_type="detail_entity",
        details={"detail": "value"},
    )

    try:
        response = client.get(
            f"/api/v1/audit/{event.id}",
            headers=auth_headers(user),
        )

        assert response.status_code == 200

        body = response.json()

        assert body["id"] == str(event.id)
        assert body["actor_user_id"] == str(user.id)
        assert body["action"] == "detail.target"
        assert body["entity_type"] == "detail_entity"
        assert body["details"] == {"detail": "value"}
    finally:
        delete_test_audit_events([event.id])
        delete_test_user(user.id)


def test_audit_detail_returns_404_for_unknown_event():
    user = create_test_user(
        full_name="Audit Missing Detail User",
    )

    assign_role_to_user(
        user_id=user.id,
        role_code="audit_compliance",
    )

    try:
        response = client.get(
            f"/api/v1/audit/{uuid4()}",
            headers=auth_headers(user),
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Audit event not found."
    finally:
        delete_test_user(user.id)


def test_audit_detail_requires_audit_permission():
    user = create_test_user(
        full_name="Audit Detail Unauthorized User",
    )

    try:
        response = client.get(
            f"/api/v1/audit/{uuid4()}",
            headers=auth_headers(user),
        )

        assert response.status_code == 403
    finally:
        delete_test_user(user.id)


def test_audit_list_rejects_invalid_date_range():
    user = create_test_user(
        full_name="Audit Invalid Date User",
    )

    assign_role_to_user(
        user_id=user.id,
        role_code="audit_compliance",
    )

    now = datetime.now(timezone.utc)

    try:
        response = client.get(
            "/api/v1/audit",
            params={
                "start_at": now.isoformat(),
                "end_at": (
                    now - timedelta(hours=1)
                ).isoformat(),
            },
            headers=auth_headers(user),
        )

        assert response.status_code == 422
        assert (
            response.json()["detail"]
            == "start_at must be earlier than or equal to end_at."
        )
    finally:
        delete_test_user(user.id)


def test_audit_endpoints_are_read_only():
    user = create_test_user(
        full_name="Audit Read Only User",
    )

    assign_role_to_user(
        user_id=user.id,
        role_code="audit_compliance",
    )

    try:
        post_response = client.post(
            "/api/v1/audit",
            headers=auth_headers(user),
            json={},
        )

        patch_response = client.patch(
            f"/api/v1/audit/{uuid4()}",
            headers=auth_headers(user),
            json={},
        )

        delete_response = client.delete(
            f"/api/v1/audit/{uuid4()}",
            headers=auth_headers(user),
        )

        assert post_response.status_code == 405
        assert patch_response.status_code == 405
        assert delete_response.status_code == 405
    finally:
        delete_test_user(user.id)


def test_inactive_audit_permission_forbids_access():
    user = create_test_user(
        full_name="Audit Inactive Permission User",
    )

    assign_role_to_user(
        user_id=user.id,
        role_code="audit_compliance",
    )

    db = SessionLocal()

    try:
        permission = db.scalar(
            select(Permission).where(
                Permission.code == "audit.read"
            )
        )

        assert permission is not None

        original_status = permission.is_active
        permission.is_active = False
        db.commit()
    finally:
        db.close()

    try:
        response = client.get(
            "/api/v1/audit",
            headers=auth_headers(user),
        )

        assert response.status_code == 403
    finally:
        db = SessionLocal()

        try:
            permission = db.scalar(
                select(Permission).where(
                    Permission.code == "audit.read"
                )
            )

            assert permission is not None

            permission.is_active = original_status
            db.commit()
        finally:
            db.close()

        delete_test_user(user.id)
from uuid import uuid4

from app.db.session import SessionLocal
from app.models.audit_event import AuditEvent
from app.models.user import User
from app.services.audit_service import record_audit_event
from app.services.auth_service import create_user


TEST_PASSWORD = "AAKAR-Audit-Service-123!"


def create_test_user() -> User:
    db = SessionLocal()

    try:
        return create_user(
            db=db,
            email=f"audit-service-{uuid4()}@example.com",
            password=TEST_PASSWORD,
            full_name="Audit Service Test User",
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


def test_record_audit_event_persists_event():
    actor = create_test_user()
    entity_id = uuid4()
    event_id = None

    db = SessionLocal()

    try:
        event = record_audit_event(
            db=db,
            actor_user_id=actor.id,
            action="user_created",
            entity_type="user",
            entity_id=entity_id,
            details={
                "email": "audit-test@example.com",
                "full_name": "Audit Test User",
            },
        )

        event_id = event.id

        assert event.id is not None
        assert event.actor_user_id == actor.id
        assert event.action == "user_created"
        assert event.entity_type == "user"
        assert event.entity_id == entity_id
        assert event.result == "success"
        assert event.details == {
            "email": "audit-test@example.com",
            "full_name": "Audit Test User",
        }
        assert event.created_at is not None
    finally:
        if event_id is not None:
            persisted_event = db.get(AuditEvent, event_id)

            if persisted_event is not None:
                db.delete(persisted_event)
                db.commit()

        db.close()
        delete_test_user(actor.id)


def test_record_audit_event_supports_null_actor():
    entity_id = uuid4()
    event_id = None

    db = SessionLocal()

    try:
        event = record_audit_event(
            db=db,
            actor_user_id=None,
            action="system_event",
            entity_type="system",
            entity_id=entity_id,
        )

        event_id = event.id

        assert event.actor_user_id is None
        assert event.action == "system_event"
        assert event.entity_type == "system"
        assert event.entity_id == entity_id
        assert event.result == "success"
        assert event.details is None
    finally:
        if event_id is not None:
            persisted_event = db.get(AuditEvent, event_id)

            if persisted_event is not None:
                db.delete(persisted_event)
                db.commit()

        db.close()


def test_record_audit_event_supports_failure_result():
    event_id = None

    db = SessionLocal()

    try:
        event = record_audit_event(
            db=db,
            actor_user_id=None,
            action="user_update",
            entity_type="user",
            entity_id=uuid4(),
            result="failure",
            details={
                "reason": "validation_failed",
            },
        )

        event_id = event.id

        assert event.result == "failure"
        assert event.details == {
            "reason": "validation_failed",
        }
    finally:
        if event_id is not None:
            persisted_event = db.get(AuditEvent, event_id)

            if persisted_event is not None:
                db.delete(persisted_event)
                db.commit()

        db.close()
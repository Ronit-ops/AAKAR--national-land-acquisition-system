from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import delete

from app.db.session import SessionLocal
from app.models.audit_event import AuditEvent
from app.models.user import User
from app.services.audit_query_service import (
    get_audit_event,
    list_audit_events,
)
from app.services.auth_service import create_user


TEST_PASSWORD = "AAKAR-Audit-Query-123!"


def create_test_user() -> User:
    db = SessionLocal()

    try:
        return create_user(
            db=db,
            email=f"audit-query-{uuid4()}@example.com",
            password=TEST_PASSWORD,
            full_name="Audit Query Test User",
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


def delete_audit_events(event_ids) -> None:
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


def test_list_audit_events_returns_newest_first():
    actor = create_test_user()
    db = SessionLocal()

    older = None
    newer = None

    try:
        now = datetime.now(timezone.utc)

        older = AuditEvent(
            actor_user_id=actor.id,
            action=f"user_created_{uuid4().hex}",
            entity_type="user",
            entity_id=uuid4(),
            result="success",
            details={"source": "test"},
            created_at=now - timedelta(minutes=5),
        )

        newer = AuditEvent(
            actor_user_id=actor.id,
            action=f"user_updated_{uuid4().hex}",
            entity_type="user",
            entity_id=uuid4(),
            result="success",
            details={"source": "test"},
            created_at=now,
        )

        db.add_all([older, newer])
        db.commit()

        events, total = list_audit_events(
            db,
            actor_user_id=actor.id,
        )

        assert total == 2
        assert len(events) == 2
        assert events[0].id == newer.id
        assert events[1].id == older.id

    finally:
        db.close()

        if older is not None and newer is not None:
            delete_audit_events([older.id, newer.id])

        delete_test_user(actor.id)


def test_list_audit_events_filters_by_action():
    actor = create_test_user()
    db = SessionLocal()

    matching = None
    other = None

    unique_action = f"user_created_{uuid4().hex}"

    try:
        matching = AuditEvent(
            actor_user_id=actor.id,
            action=unique_action,
            entity_type="user",
            entity_id=uuid4(),
            result="success",
        )

        other = AuditEvent(
            actor_user_id=actor.id,
            action=f"user_updated_{uuid4().hex}",
            entity_type="user",
            entity_id=uuid4(),
            result="success",
        )

        db.add_all([matching, other])
        db.commit()

        results, total = list_audit_events(
            db,
            action=unique_action.upper(),
        )

        assert total == 1
        assert len(results) == 1
        assert results[0].id == matching.id

    finally:
        db.close()

        if matching is not None and other is not None:
            delete_audit_events([matching.id, other.id])

        delete_test_user(actor.id)


def test_list_audit_events_filters_by_entity_type_and_result():
    actor = create_test_user()
    db = SessionLocal()

    matching = None
    non_matching = None

    unique_entity_type = f"test_entity_{uuid4().hex}"

    try:
        matching = AuditEvent(
            actor_user_id=actor.id,
            action=f"action_{uuid4().hex}",
            entity_type=unique_entity_type,
            entity_id=uuid4(),
            result="success",
        )

        non_matching = AuditEvent(
            actor_user_id=actor.id,
            action=f"action_{uuid4().hex}",
            entity_type=f"other_entity_{uuid4().hex}",
            entity_id=uuid4(),
            result="failure",
        )

        db.add_all([matching, non_matching])
        db.commit()

        results, total = list_audit_events(
            db,
            entity_type=unique_entity_type.upper(),
            result="SUCCESS",
        )

        assert total == 1
        assert len(results) == 1
        assert results[0].id == matching.id

    finally:
        db.close()

        if matching is not None and non_matching is not None:
            delete_audit_events(
                [matching.id, non_matching.id]
            )

        delete_test_user(actor.id)


def test_list_audit_events_filters_by_entity_id():
    actor = create_test_user()
    db = SessionLocal()

    matching = None
    other = None
    target_id = uuid4()

    try:
        matching = AuditEvent(
            actor_user_id=actor.id,
            action=f"user_updated_{uuid4().hex}",
            entity_type="user",
            entity_id=target_id,
            result="success",
        )

        other = AuditEvent(
            actor_user_id=actor.id,
            action=f"user_updated_{uuid4().hex}",
            entity_type="user",
            entity_id=uuid4(),
            result="success",
        )

        db.add_all([matching, other])
        db.commit()

        results, total = list_audit_events(
            db,
            entity_id=target_id,
        )

        assert total == 1
        assert len(results) == 1
        assert results[0].id == matching.id

    finally:
        db.close()

        if matching is not None and other is not None:
            delete_audit_events([matching.id, other.id])

        delete_test_user(actor.id)


def test_list_audit_events_filters_by_search():
    actor = create_test_user()
    db = SessionLocal()

    matching = None
    other = None

    unique_search_term = f"uniqueaudit{uuid4().hex}"

    try:
        matching = AuditEvent(
            actor_user_id=actor.id,
            action=f"{unique_search_term}_created",
            entity_type="permission",
            entity_id=uuid4(),
            result="success",
        )

        other = AuditEvent(
            actor_user_id=actor.id,
            action=f"other_action_{uuid4().hex}",
            entity_type="user",
            entity_id=uuid4(),
            result="success",
        )

        db.add_all([matching, other])
        db.commit()

        results, total = list_audit_events(
            db,
            search=unique_search_term.upper(),
        )

        assert total == 1
        assert len(results) == 1
        assert results[0].id == matching.id

    finally:
        db.close()

        if matching is not None and other is not None:
            delete_audit_events([matching.id, other.id])

        delete_test_user(actor.id)


def test_list_audit_events_filters_by_date_range():
    actor = create_test_user()
    db = SessionLocal()

    event = None

    try:
        event_time = datetime.now(timezone.utc) - timedelta(hours=1)

        event = AuditEvent(
            actor_user_id=actor.id,
            action=f"user_created_{uuid4().hex}",
            entity_type="user",
            entity_id=uuid4(),
            result="success",
            created_at=event_time,
        )

        db.add(event)
        db.commit()

        start_at = event_time - timedelta(minutes=5)
        end_at = event_time + timedelta(minutes=5)

        results, total = list_audit_events(
            db,
            actor_user_id=actor.id,
            start_at=start_at,
            end_at=end_at,
        )

        assert total == 1
        assert len(results) == 1
        assert results[0].id == event.id

    finally:
        db.close()

        if event is not None:
            delete_audit_events([event.id])

        delete_test_user(actor.id)


def test_list_audit_events_paginates():
    actor = create_test_user()
    db = SessionLocal()

    events = []

    try:
        for index in range(3):
            events.append(
                AuditEvent(
                    actor_user_id=actor.id,
                    action=f"pagination_test_{index}_{uuid4().hex}",
                    entity_type="pagination_test",
                    entity_id=uuid4(),
                    result="success",
                )
            )

        db.add_all(events)
        db.commit()

        results, total = list_audit_events(
            db,
            actor_user_id=actor.id,
            offset=1,
            limit=1,
        )

        assert total == 3
        assert len(results) == 1

    finally:
        db.close()

        if events:
            delete_audit_events(
                [event.id for event in events]
            )

        delete_test_user(actor.id)


def test_get_audit_event_returns_event():
    db = SessionLocal()
    event = None

    try:
        event = AuditEvent(
            actor_user_id=None,
            action=f"test_event_{uuid4().hex}",
            entity_type="test",
            result="success",
        )

        db.add(event)
        db.commit()

        found = get_audit_event(
            db,
            event_id=event.id,
        )

        assert found is not None
        assert found.id == event.id
        assert found.action == event.action

    finally:
        db.close()

        if event is not None:
            delete_audit_events([event.id])


def test_get_audit_event_returns_none_for_unknown_id():
    db = SessionLocal()

    try:
        found = get_audit_event(
            db,
            event_id=uuid4(),
        )

        assert found is None

    finally:
        db.close()
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models.audit_event import AuditEvent
from app.models.authority import Authority
from app.models.department import Department
from app.models.project import Project
from app.models.user import User
from app.services.project_service import (
    PROJECT_STATUS_ACTIVE,
    PROJECT_STATUS_CLOSED,
    PROJECT_STATUS_DRAFT,
    activate_project,
    close_project,
    create_project,
    get_project,
    list_projects,
    update_project,
)


TEST_CODE_PREFIX = "PROJECT-SERVICE-TEST"


def create_test_user() -> User:
    db = SessionLocal()

    try:
        user = User(
            email=f"project-service-{uuid4()}@example.com",
            full_name="Project Service Test User",
            password_hash="test-password-hash",
            is_active=True,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        return user
    finally:
        db.close()


def create_test_authority(
    *,
    active: bool = True,
) -> tuple[Authority, Department]:
    db = SessionLocal()

    try:
        department = Department(
            code=f"PRJ-DPT-{uuid4().hex[:8].upper()}",
            name="Project Test Department",
            description="Project service test department",
            is_active=True,
        )

        db.add(department)
        db.commit()
        db.refresh(department)

        authority = Authority(
            department_id=department.id,
            code=f"PRJ-AUTH-{uuid4().hex[:8].upper()}",
            name="Project Test Authority",
            authority_type="STATE",
            is_active=active,
        )

        db.add(authority)
        db.commit()
        db.refresh(authority)

        return authority, department
    finally:
        db.close()


def delete_test_project(project_id) -> None:
    db = SessionLocal()

    try:
        project = db.get(Project, project_id)

        if project is not None:
            db.delete(project)
            db.commit()
    finally:
        db.close()


def delete_test_authority(
    authority_id,
    department_id,
) -> None:
    db = SessionLocal()

    try:
        authority = db.get(
            Authority,
            authority_id,
        )

        if authority is not None:
            db.delete(authority)
            db.commit()

        department = db.get(
            Department,
            department_id,
        )

        if department is not None:
            db.delete(department)
            db.commit()
    finally:
        db.close()


def delete_test_user(user_id) -> None:
    db = SessionLocal()

    try:
        db.query(AuditEvent).filter(
            AuditEvent.actor_user_id == user_id
        ).delete(
            synchronize_session=False
        )

        user = db.get(User, user_id)

        if user is not None:
            db.delete(user)

        db.commit()
    finally:
        db.close()


def cleanup_project_audits(project_id) -> None:
    db = SessionLocal()

    try:
        db.query(AuditEvent).filter(
            AuditEvent.entity_type == "project",
            AuditEvent.entity_id == project_id,
        ).delete(
            synchronize_session=False
        )

        db.commit()
    finally:
        db.close()


def test_create_project_creates_draft_project():
    user = create_test_user()
    authority, department = create_test_authority()

    project = None

    db = SessionLocal()

    try:
        project = create_project(
            db,
            code=f"{TEST_CODE_PREFIX}-{uuid4().hex[:8]}",
            name="National Highway Expansion",
            sector="Transport",
            description="Test infrastructure project",
            responsible_authority_id=authority.id,
            boundary=None,
            actor_user_id=user.id,
        )

        assert project.id is not None
        assert project.status == PROJECT_STATUS_DRAFT
        assert project.created_by_user_id == user.id
        assert project.updated_by_user_id == user.id
        assert project.responsible_authority_id == authority.id

        persisted = get_project(
            db,
            project.id,
        )

        assert persisted is not None
        assert persisted.code == project.code
        assert persisted.status == PROJECT_STATUS_DRAFT

    finally:
        db.close()

        if project is not None:
            cleanup_project_audits(project.id)
            delete_test_project(project.id)

        delete_test_authority(
            authority.id,
            department.id,
        )
        delete_test_user(user.id)


def test_create_project_rejects_inactive_authority():
    user = create_test_user()
    authority, department = create_test_authority(
        active=False,
    )

    db = SessionLocal()

    try:
        with pytest.raises(
            ValueError,
            match="inactive authority",
        ):
            create_project(
                db,
                code=f"{TEST_CODE_PREFIX}-{uuid4().hex[:8]}",
                name="Inactive Authority Project",
                sector="Transport",
                description=None,
                responsible_authority_id=authority.id,
                boundary=None,
                actor_user_id=user.id,
            )
    finally:
        db.close()

        delete_test_authority(
            authority.id,
            department.id,
        )
        delete_test_user(user.id)


def test_create_project_rejects_duplicate_code():
    user = create_test_user()
    authority, department = create_test_authority()

    code = f"{TEST_CODE_PREFIX}-{uuid4().hex[:8]}"

    first_project = None

    db = SessionLocal()

    try:
        first_project = create_project(
            db,
            code=code,
            name="First Project",
            sector="Transport",
            description=None,
            responsible_authority_id=authority.id,
            boundary=None,
            actor_user_id=user.id,
        )

        with pytest.raises(
            ValueError,
            match="already exists",
        ):
            create_project(
                db,
                code=code.lower(),
                name="Duplicate Project",
                sector="Transport",
                description=None,
                responsible_authority_id=authority.id,
                boundary=None,
                actor_user_id=user.id,
            )

    finally:
        db.close()

        if first_project is not None:
            cleanup_project_audits(first_project.id)
            delete_test_project(first_project.id)

        delete_test_authority(
            authority.id,
            department.id,
        )
        delete_test_user(user.id)


def test_list_projects_supports_search_and_pagination():
    user = create_test_user()
    authority, department = create_test_authority()

    first_project = None
    second_project = None

    db = SessionLocal()

    try:
        first_project = create_project(
            db,
            code=f"{TEST_CODE_PREFIX}-ROAD-{uuid4().hex[:8]}",
            name="Western Corridor",
            sector="Transport",
            description=None,
            responsible_authority_id=authority.id,
            boundary=None,
            actor_user_id=user.id,
        )

        second_project = create_project(
            db,
            code=f"{TEST_CODE_PREFIX}-RAIL-{uuid4().hex[:8]}",
            name="Western Railway Expansion",
            sector="Rail",
            description=None,
            responsible_authority_id=authority.id,
            boundary=None,
            actor_user_id=user.id,
        )

        projects, total = list_projects(
            db,
            search="Western",
            offset=0,
            limit=10,
        )

        project_ids = {
            project.id
            for project in projects
        }

        assert total == 2
        assert first_project.id in project_ids
        assert second_project.id in project_ids

        projects, total = list_projects(
            db,
            search="Western",
            offset=0,
            limit=1,
        )

        assert total == 2
        assert len(projects) == 1

    finally:
        db.close()

        if first_project is not None:
            cleanup_project_audits(first_project.id)
            delete_test_project(first_project.id)

        if second_project is not None:
            cleanup_project_audits(second_project.id)
            delete_test_project(second_project.id)

        delete_test_authority(
            authority.id,
            department.id,
        )
        delete_test_user(user.id)


def test_update_project_updates_project_data():
    user = create_test_user()
    authority, department = create_test_authority()

    project = None

    db = SessionLocal()

    try:
        project = create_project(
            db,
            code=f"{TEST_CODE_PREFIX}-{uuid4().hex[:8]}",
            name="Original Project",
            sector="Transport",
            description="Original description",
            responsible_authority_id=authority.id,
            boundary=None,
            actor_user_id=user.id,
        )

        updated = update_project(
            db,
            project_id=project.id,
            code=project.code,
            name="Updated Project",
            sector="Energy",
            description="Updated description",
            responsible_authority_id=authority.id,
            boundary=None,
            actor_user_id=user.id,
        )

        assert updated.name == "Updated Project"
        assert updated.sector == "Energy"
        assert updated.description == "Updated description"
        assert updated.updated_by_user_id == user.id
        assert updated.status == PROJECT_STATUS_DRAFT

    finally:
        db.close()

        if project is not None:
            cleanup_project_audits(project.id)
            delete_test_project(project.id)

        delete_test_authority(
            authority.id,
            department.id,
        )
        delete_test_user(user.id)


def test_closed_project_cannot_be_updated():
    user = create_test_user()
    authority, department = create_test_authority()

    project = None

    db = SessionLocal()

    try:
        project = create_project(
            db,
            code=f"{TEST_CODE_PREFIX}-{uuid4().hex[:8]}",
            name="Closed Project",
            sector="Transport",
            description=None,
            responsible_authority_id=authority.id,
            boundary=None,
            actor_user_id=user.id,
        )

        activate_project(
            db,
            project_id=project.id,
            actor_user_id=user.id,
        )

        close_project(
            db,
            project_id=project.id,
            actor_user_id=user.id,
        )

        with pytest.raises(
            ValueError,
            match="Closed projects cannot be updated",
        ):
            update_project(
                db,
                project_id=project.id,
                code=project.code,
                name="Should Fail",
                sector=project.sector,
                description=None,
                responsible_authority_id=authority.id,
                boundary=None,
                actor_user_id=user.id,
            )

    finally:
        db.close()

        if project is not None:
            cleanup_project_audits(project.id)
            delete_test_project(project.id)

        delete_test_authority(
            authority.id,
            department.id,
        )
        delete_test_user(user.id)


def test_project_lifecycle_is_draft_active_closed():
    user = create_test_user()
    authority, department = create_test_authority()

    project = None

    db = SessionLocal()

    try:
        project = create_project(
            db,
            code=f"{TEST_CODE_PREFIX}-{uuid4().hex[:8]}",
            name="Lifecycle Project",
            sector="Transport",
            description=None,
            responsible_authority_id=authority.id,
            boundary=None,
            actor_user_id=user.id,
        )

        assert project.status == PROJECT_STATUS_DRAFT

        activated = activate_project(
            db,
            project_id=project.id,
            actor_user_id=user.id,
        )

        assert activated.status == PROJECT_STATUS_ACTIVE

        closed = close_project(
            db,
            project_id=project.id,
            actor_user_id=user.id,
        )

        assert closed.status == PROJECT_STATUS_CLOSED

    finally:
        db.close()

        if project is not None:
            cleanup_project_audits(project.id)
            delete_test_project(project.id)

        delete_test_authority(
            authority.id,
            department.id,
        )
        delete_test_user(user.id)


def test_project_cannot_skip_draft_to_closed():
    user = create_test_user()
    authority, department = create_test_authority()

    project = None

    db = SessionLocal()

    try:
        project = create_project(
            db,
            code=f"{TEST_CODE_PREFIX}-{uuid4().hex[:8]}",
            name="Invalid Lifecycle Project",
            sector="Transport",
            description=None,
            responsible_authority_id=authority.id,
            boundary=None,
            actor_user_id=user.id,
        )

        with pytest.raises(
            ValueError,
            match="Only active projects can be closed",
        ):
            close_project(
                db,
                project_id=project.id,
                actor_user_id=user.id,
            )

    finally:
        db.close()

        if project is not None:
            cleanup_project_audits(project.id)
            delete_test_project(project.id)

        delete_test_authority(
            authority.id,
            department.id,
        )
        delete_test_user(user.id)


def test_active_project_cannot_be_activated_again():
    user = create_test_user()
    authority, department = create_test_authority()

    project = None

    db = SessionLocal()

    try:
        project = create_project(
            db,
            code=f"{TEST_CODE_PREFIX}-{uuid4().hex[:8]}",
            name="Already Active Project",
            sector="Transport",
            description=None,
            responsible_authority_id=authority.id,
            boundary=None,
            actor_user_id=user.id,
        )

        activate_project(
            db,
            project_id=project.id,
            actor_user_id=user.id,
        )

        with pytest.raises(
            ValueError,
            match="Only draft projects can be activated",
        ):
            activate_project(
                db,
                project_id=project.id,
                actor_user_id=user.id,
            )

    finally:
        db.close()

        if project is not None:
            cleanup_project_audits(project.id)
            delete_test_project(project.id)

        delete_test_authority(
            authority.id,
            department.id,
        )
        delete_test_user(user.id)


def test_closed_project_cannot_be_reactivated():
    user = create_test_user()
    authority, department = create_test_authority()

    project = None

    db = SessionLocal()

    try:
        project = create_project(
            db,
            code=f"{TEST_CODE_PREFIX}-{uuid4().hex[:8]}",
            name="Closed Project",
            sector="Transport",
            description=None,
            responsible_authority_id=authority.id,
            boundary=None,
            actor_user_id=user.id,
        )

        activate_project(
            db,
            project_id=project.id,
            actor_user_id=user.id,
        )

        close_project(
            db,
            project_id=project.id,
            actor_user_id=user.id,
        )

        with pytest.raises(
            ValueError,
            match="Only draft projects can be activated",
        ):
            activate_project(
                db,
                project_id=project.id,
                actor_user_id=user.id,
            )

    finally:
        db.close()

        if project is not None:
            cleanup_project_audits(project.id)
            delete_test_project(project.id)

        delete_test_authority(
            authority.id,
            department.id,
        )
        delete_test_user(user.id)


def test_invalid_project_boundary_is_rejected():
    user = create_test_user()
    authority, department = create_test_authority()

    db = SessionLocal()

    try:
        with pytest.raises(
            ValueError,
            match="Polygon or MultiPolygon",
        ):
            create_project(
                db,
                code=f"{TEST_CODE_PREFIX}-{uuid4().hex[:8]}",
                name="Invalid Boundary Project",
                sector="Transport",
                description=None,
                responsible_authority_id=authority.id,
                boundary={
                    "type": "Point",
                    "coordinates": [73.8567, 18.5204],
                },
                actor_user_id=user.id,
            )
    finally:
        db.close()

        delete_test_authority(
            authority.id,
            department.id,
        )
        delete_test_user(user.id)


def test_polygon_boundary_is_stored_as_multipolygon():
    user = create_test_user()
    authority, department = create_test_authority()

    project = None

    db = SessionLocal()

    try:
        project = create_project(
            db,
            code=f"{TEST_CODE_PREFIX}-{uuid4().hex[:8]}",
            name="Spatial Project",
            sector="Transport",
            description=None,
            responsible_authority_id=authority.id,
            boundary={
                "type": "Polygon",
                "coordinates": [
                    [
                        [73.8500, 18.5200],
                        [73.8600, 18.5200],
                        [73.8600, 18.5300],
                        [73.8500, 18.5300],
                        [73.8500, 18.5200],
                    ]
                ],
            },
            actor_user_id=user.id,
        )

        assert project.boundary is not None

        geometry_type = db.scalar(
            select(
                func.GeometryType(Project.boundary)
            ).where(
                Project.id == project.id
            )
        )

        assert geometry_type == "MULTIPOLYGON"

    finally:
        db.close()

        if project is not None:
            cleanup_project_audits(project.id)
            delete_test_project(project.id)

        delete_test_authority(
            authority.id,
            department.id,
        )
        delete_test_user(user.id)
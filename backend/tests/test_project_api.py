from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.core.jwt import create_access_token
from app.db.session import SessionLocal
from app.main import app
from app.models.audit_event import AuditEvent
from app.models.authority import Authority
from app.models.department import Department
from app.models.project import Project
from app.models.user import User
from app.services.auth_service import create_user
from app.services.rbac_service import (
    assign_permission_to_role,
    assign_role,
)


client = TestClient(app)

TEST_PASSWORD = "AAKAR-Project-API-123!"

PROJECT_READ = "project.read"
PROJECT_CREATE = "project.create"
PROJECT_UPDATE = "project.update"
PROJECT_ACTIVATE = "project.activate"
PROJECT_CLOSE = "project.close"


def create_test_user(
    *,
    full_name: str,
) -> User:
    db = SessionLocal()

    try:
        return create_user(
            db=db,
            email=f"project-api-{uuid4()}@example.com",
            password=TEST_PASSWORD,
            full_name=full_name,
        )
    finally:
        db.close()


def assign_test_role(
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


def create_authority() -> tuple[Authority, Department]:
    db = SessionLocal()

    try:
        department = Department(
            code=f"API-DPT-{uuid4().hex[:8].upper()}",
            name="Project API Test Department",
            description="Project API test department",
            is_active=True,
        )

        db.add(department)
        db.commit()
        db.refresh(department)

        authority = Authority(
            department_id=department.id,
            code=f"API-AUTH-{uuid4().hex[:8].upper()}",
            name="Project API Test Authority",
            authority_type="STATE",
            is_active=True,
        )

        db.add(authority)
        db.commit()
        db.refresh(authority)

        return authority, department
    finally:
        db.close()


def delete_project(project_id) -> None:
    db = SessionLocal()

    try:
        db.execute(
            delete(AuditEvent).where(
                AuditEvent.entity_type == "project",
                AuditEvent.entity_id == project_id,
            )
        )

        project = db.get(Project, project_id)

        if project is not None:
            db.delete(project)

        db.commit()
    finally:
        db.close()


def delete_authority(
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


def delete_user(user_id) -> None:
    db = SessionLocal()

    try:
        db.execute(
            delete(AuditEvent).where(
                AuditEvent.actor_user_id == user_id,
            )
        )

        user = db.get(
            User,
            user_id,
        )

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


def project_payload(
    authority_id,
    *,
    code: str | None = None,
) -> dict:
    return {
        "code": code or f"API-PROJECT-{uuid4().hex[:8].upper()}",
        "name": "API Test Project",
        "sector": "Transport",
        "description": "Project API integration test",
        "responsible_authority_id": str(authority_id),
        "boundary": None,
    }


def test_project_list_requires_authentication():
    response = client.get("/api/v1/projects")

    assert response.status_code == 401


def test_project_list_requires_permission():
    user = create_test_user(
        full_name="Project API Unauthorized User",
    )

    try:
        response = client.get(
            "/api/v1/projects",
            headers=auth_headers(user),
        )

        assert response.status_code == 403
    finally:
        delete_user(user.id)


def test_project_create_requires_permission():
    user = create_test_user(
        full_name="Project API Create Unauthorized User",
    )
    authority, department = create_authority()

    try:
        response = client.post(
            "/api/v1/projects",
            json=project_payload(authority.id),
            headers=auth_headers(user),
        )

        assert response.status_code == 403

    finally:
        delete_authority(
            authority.id,
            department.id,
        )
        delete_user(user.id)


def test_project_create_and_get():
    user = create_test_user(
        full_name="Project API Administrator",
    )

    assign_test_role(
        user_id=user.id,
        role_code="project_director",
    )

    authority, department = create_authority()

    project_id = None

    try:
        response = client.post(
            "/api/v1/projects",
            json=project_payload(authority.id),
            headers=auth_headers(user),
        )

        assert response.status_code == 201

        body = response.json()

        assert body["name"] == "API Test Project"
        assert body["sector"] == "Transport"
        assert body["status"] == "DRAFT"
        assert body["responsible_authority_id"] == str(
            authority.id
        )

        project_id = body["id"]

        response = client.get(
            f"/api/v1/projects/{project_id}",
            headers=auth_headers(user),
        )

        assert response.status_code == 200

        body = response.json()

        assert body["id"] == project_id
        assert body["code"] is not None
        assert body["status"] == "DRAFT"

    finally:
        if project_id is not None:
            delete_project(project_id)

        delete_authority(
            authority.id,
            department.id,
        )
        delete_user(user.id)


def test_project_list_returns_created_project():
    user = create_test_user(
        full_name="Project API List User",
    )

    assign_test_role(
        user_id=user.id,
        role_code="project_director",
    )

    authority, department = create_authority()

    project_id = None

    try:
        create_response = client.post(
            "/api/v1/projects",
            json=project_payload(
                authority.id,
                code=f"API-LIST-{uuid4().hex[:8].upper()}",
            ),
            headers=auth_headers(user),
        )

        assert create_response.status_code == 201

        project_id = create_response.json()["id"]

        response = client.get(
            "/api/v1/projects",
            headers=auth_headers(user),
        )

        assert response.status_code == 200

        body = response.json()

        assert "items" in body
        assert "total" in body
        assert "offset" in body
        assert "limit" in body

        assert any(
            item["id"] == project_id
            for item in body["items"]
        )

    finally:
        if project_id is not None:
            delete_project(project_id)

        delete_authority(
            authority.id,
            department.id,
        )
        delete_user(user.id)


def test_project_search():
    user = create_test_user(
        full_name="Project API Search User",
    )

    assign_test_role(
        user_id=user.id,
        role_code="project_director",
    )

    authority, department = create_authority()

    project_id = None

    try:
        create_response = client.post(
            "/api/v1/projects",
            json={
                **project_payload(authority.id),
                "name": "Unique API Search Project",
            },
            headers=auth_headers(user),
        )

        assert create_response.status_code == 201

        project_id = create_response.json()["id"]

        response = client.get(
            "/api/v1/projects",
            params={
                "search": "Unique API Search Project",
            },
            headers=auth_headers(user),
        )

        assert response.status_code == 200

        body = response.json()

        assert body["total"] >= 1

        assert any(
            item["id"] == project_id
            for item in body["items"]
        )

    finally:
        if project_id is not None:
            delete_project(project_id)

        delete_authority(
            authority.id,
            department.id,
        )
        delete_user(user.id)


def test_project_update():
    user = create_test_user(
        full_name="Project API Update User",
    )

    assign_test_role(
        user_id=user.id,
        role_code="project_director",
    )

    authority, department = create_authority()

    project_id = None

    try:
        create_response = client.post(
            "/api/v1/projects",
            json=project_payload(authority.id),
            headers=auth_headers(user),
        )

        assert create_response.status_code == 201

        created = create_response.json()
        project_id = created["id"]

        update_payload = {
            **project_payload(
                authority.id,
                code=created["code"],
            ),
            "name": "Updated API Project",
            "sector": "Energy",
            "description": "Updated project description",
        }

        response = client.put(
            f"/api/v1/projects/{project_id}",
            json=update_payload,
            headers=auth_headers(user),
        )

        assert response.status_code == 200

        body = response.json()

        assert body["name"] == "Updated API Project"
        assert body["sector"] == "Energy"
        assert body["description"] == (
            "Updated project description"
        )
        assert body["status"] == "DRAFT"

    finally:
        if project_id is not None:
            delete_project(project_id)

        delete_authority(
            authority.id,
            department.id,
        )
        delete_user(user.id)


def test_project_update_requires_permission():
    creator = create_test_user(
        full_name="Project API Creator",
    )

    assign_test_role(
        user_id=creator.id,
        role_code="project_director",
    )

    unauthorized = create_test_user(
        full_name="Project API Unauthorized Updater",
    )

    authority, department = create_authority()

    project_id = None

    try:
        create_response = client.post(
            "/api/v1/projects",
            json=project_payload(authority.id),
            headers=auth_headers(creator),
        )

        assert create_response.status_code == 201

        project_id = create_response.json()["id"]

        response = client.put(
            f"/api/v1/projects/{project_id}",
            json=project_payload(
                authority.id,
                code=create_response.json()["code"],
            ),
            headers=auth_headers(unauthorized),
        )

        assert response.status_code == 403

    finally:
        if project_id is not None:
            delete_project(project_id)

        delete_authority(
            authority.id,
            department.id,
        )
        delete_user(creator.id)
        delete_user(unauthorized.id)


def test_project_not_found_returns_404():
    user = create_test_user(
        full_name="Project API Not Found User",
    )

    assign_test_role(
        user_id=user.id,
        role_code="project_director",
    )

    try:
        response = client.get(
            f"/api/v1/projects/{uuid4()}",
            headers=auth_headers(user),
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Project not found."

    finally:
        delete_user(user.id)


def test_project_duplicate_code_returns_409():
    user = create_test_user(
        full_name="Project API Duplicate User",
    )

    assign_test_role(
        user_id=user.id,
        role_code="project_director",
    )

    authority, department = create_authority()

    project_id = None

    try:
        code = f"API-DUP-{uuid4().hex[:8].upper()}"

        first_response = client.post(
            "/api/v1/projects",
            json=project_payload(
                authority.id,
                code=code,
            ),
            headers=auth_headers(user),
        )

        assert first_response.status_code == 201

        project_id = first_response.json()["id"]

        second_response = client.post(
            "/api/v1/projects",
            json=project_payload(
                authority.id,
                code=code,
            ),
            headers=auth_headers(user),
        )

        assert second_response.status_code == 400

    finally:
        if project_id is not None:
            delete_project(project_id)

        delete_authority(
            authority.id,
            department.id,
        )
        delete_user(user.id)


def test_project_validation_returns_422():
    user = create_test_user(
        full_name="Project API Validation User",
    )

    assign_test_role(
        user_id=user.id,
        role_code="project_director",
    )

    authority, department = create_authority()

    try:
        response = client.post(
            "/api/v1/projects",
            json={
                "code": "",
                "name": "A",
                "sector": "",
                "description": None,
                "responsible_authority_id": str(
                    authority.id
                ),
                "boundary": None,
            },
            headers=auth_headers(user),
        )

        assert response.status_code == 422

    finally:
        delete_authority(
            authority.id,
            department.id,
        )
        delete_user(user.id)


def test_project_activate_and_close():
    user = create_test_user(
        full_name="Project API Lifecycle User",
    )

    assign_test_role(
        user_id=user.id,
        role_code="project_director",
    )

    authority, department = create_authority()

    project_id = None

    try:
        create_response = client.post(
            "/api/v1/projects",
            json=project_payload(authority.id),
            headers=auth_headers(user),
        )

        assert create_response.status_code == 201

        project_id = create_response.json()["id"]

        activate_response = client.post(
            f"/api/v1/projects/{project_id}/activate",
            headers=auth_headers(user),
        )

        assert activate_response.status_code == 200

        assert activate_response.json()["status"] == "ACTIVE"

        close_response = client.post(
            f"/api/v1/projects/{project_id}/close",
            headers=auth_headers(user),
        )

        assert close_response.status_code == 200

        assert close_response.json()["status"] == "CLOSED"

    finally:
        if project_id is not None:
            delete_project(project_id)

        delete_authority(
            authority.id,
            department.id,
        )
        delete_user(user.id)


def test_project_cannot_close_directly_from_draft():
    user = create_test_user(
        full_name="Project API Invalid Lifecycle User",
    )

    assign_test_role(
        user_id=user.id,
        role_code="project_director",
    )

    authority, department = create_authority()

    project_id = None

    try:
        create_response = client.post(
            "/api/v1/projects",
            json=project_payload(authority.id),
            headers=auth_headers(user),
        )

        assert create_response.status_code == 201

        project_id = create_response.json()["id"]

        response = client.post(
            f"/api/v1/projects/{project_id}/close",
            headers=auth_headers(user),
        )

        assert response.status_code == 400

    finally:
        if project_id is not None:
            delete_project(project_id)

        delete_authority(
            authority.id,
            department.id,
        )
        delete_user(user.id)


def test_project_activate_requires_permission():
    user = create_test_user(
        full_name="Project API Activation Unauthorized User",
    )

    authority, department = create_authority()

    try:
        response = client.post(
            f"/api/v1/projects/{uuid4()}/activate",
            headers=auth_headers(user),
        )

        assert response.status_code == 403

    finally:
        delete_authority(
            authority.id,
            department.id,
        )
        delete_user(user.id)


def test_project_close_requires_permission():
    user = create_test_user(
        full_name="Project API Close Unauthorized User",
    )

    authority, department = create_authority()

    try:
        response = client.post(
            f"/api/v1/projects/{uuid4()}/close",
            headers=auth_headers(user),
        )

        assert response.status_code == 403

    finally:
        delete_authority(
            authority.id,
            department.id,
        )
        delete_user(user.id)
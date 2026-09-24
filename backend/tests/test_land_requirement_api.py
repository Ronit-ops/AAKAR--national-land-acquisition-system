from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.core.jwt import create_access_token
from app.db.session import SessionLocal
from app.main import app
from app.models.audit_event import AuditEvent
from app.models.authority import Authority
from app.models.department import Department
from app.models.land_requirement import LandRequirement
from app.models.project import Project
from app.models.user import User
from app.services.auth_service import create_user
from app.services.rbac_service import assign_role


client = TestClient(app)

TEST_PASSWORD = "AAKAR-Land-Requirement-API-123!"

LAND_REQUIREMENT_PATH = "/api/v1/land-requirements"
PROJECT_PATH = "/api/v1/projects"


def create_test_user(
    *,
    full_name: str,
) -> User:
    db = SessionLocal()

    try:
        return create_user(
            db=db,
            email=f"land-requirement-api-{uuid4()}@example.com",
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


def auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(user.id)

    return {
        "Authorization": f"Bearer {token}",
    }


def create_authority() -> tuple[Authority, Department]:
    db = SessionLocal()

    try:
        department = Department(
            code=f"LR-DPT-{uuid4().hex[:8].upper()}",
            name="Land Requirement Test Department",
            description="Land Requirement API test department",
            is_active=True,
        )

        db.add(department)
        db.commit()
        db.refresh(department)

        authority = Authority(
            department_id=department.id,
            code=f"LR-AUTH-{uuid4().hex[:8].upper()}",
            name="Land Requirement Test Authority",
            authority_type="STATE",
            is_active=True,
        )

        db.add(authority)
        db.commit()
        db.refresh(authority)

        return authority, department

    finally:
        db.close()


def delete_land_requirement(
    land_requirement_id,
) -> None:
    db = SessionLocal()

    try:
        db.execute(
            delete(AuditEvent).where(
                AuditEvent.entity_type == "land_requirement",
                AuditEvent.entity_id == land_requirement_id,
            )
        )

        land_requirement = db.get(
            LandRequirement,
            land_requirement_id,
        )

        if land_requirement is not None:
            db.delete(land_requirement)

        db.commit()

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

        project = db.get(
            Project,
            project_id,
        )

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


def project_payload(
    authority_id,
    *,
    code: str | None = None,
) -> dict:
    return {
        "code": code or f"LR-PROJECT-{uuid4().hex[:8].upper()}",
        "name": "Land Requirement API Test Project",
        "sector": "Transport",
        "description": "Land Requirement API integration test",
        "responsible_authority_id": str(authority_id),
        "boundary": None,
    }


def land_requirement_payload(
    project_id,
    *,
    requirement_reference: str | None = None,
) -> dict:
    return {
        "project_id": str(project_id),
        "requirement_reference": (
            requirement_reference
            or f"LR-{uuid4().hex[:8].upper()}"
        ),
        "purpose": "Land requirement for project development",
        "required_area_sq_m": 25000,
        "state": "Maharashtra",
        "district": "Pune",
        "taluka": "Haveli",
        "village": "Wagholi",
        "description": "Land Requirement API integration test",
    }


def create_project(
    user: User,
    authority_id,
) -> str:
    response = client.post(
        PROJECT_PATH,
        json=project_payload(authority_id),
        headers=auth_headers(user),
    )

    assert response.status_code == 201

    return response.json()["id"]


def create_land_requirement(
    user: User,
    project_id,
    *,
    requirement_reference: str | None = None,
) -> dict:
    response = client.post(
        LAND_REQUIREMENT_PATH,
        json=land_requirement_payload(
            project_id,
            requirement_reference=requirement_reference,
        ),
        headers=auth_headers(user),
    )

    assert response.status_code == 201

    return response.json()


def test_land_requirement_list_requires_authentication():
    response = client.get(LAND_REQUIREMENT_PATH)

    assert response.status_code == 401


def test_land_requirement_create_requires_permission():
    user = create_test_user(
        full_name="Land Requirement Unauthorized User",
    )

    authority, department = create_authority()
    project_id = None

    try:
        project_creator = create_test_user(
            full_name="Land Requirement Project Creator",
        )

        try:
            assign_test_role(
                user_id=project_creator.id,
                role_code="project_director",
            )

            project_id = create_project(
                project_creator,
                authority.id,
            )

            response = client.post(
                LAND_REQUIREMENT_PATH,
                json=land_requirement_payload(project_id),
                headers=auth_headers(user),
            )

            assert response.status_code == 403

        finally:
            if project_id is not None:
                delete_project(project_id)

            delete_user(project_creator.id)

    finally:
        delete_authority(
            authority.id,
            department.id,
        )
        delete_user(user.id)


def test_land_requirement_create_get_and_list():
    user = create_test_user(
        full_name="Land Requirement API Administrator",
    )

    assign_test_role(
        user_id=user.id,
        role_code="project_director",
    )

    authority, department = create_authority()

    project_id = None
    land_requirement_id = None

    try:
        project_id = create_project(
            user,
            authority.id,
        )

        requirement = create_land_requirement(
            user,
            project_id,
            requirement_reference="LR-CRUD-001",
        )

        land_requirement_id = requirement["id"]

        assert requirement["project_id"] == project_id
        assert requirement["requirement_reference"] == (
            "LR-CRUD-001"
        )
        assert requirement["required_area_sq_m"] == "25000.0000"
        assert requirement["status"] == "DRAFT"

        get_response = client.get(
            f"{LAND_REQUIREMENT_PATH}/{land_requirement_id}",
            headers=auth_headers(user),
        )

        assert get_response.status_code == 200

        get_body = get_response.json()

        assert get_body["id"] == land_requirement_id
        assert get_body["project_id"] == project_id
        assert get_body["status"] == "DRAFT"

        list_response = client.get(
            LAND_REQUIREMENT_PATH,
            params={
                "project_id": project_id,
            },
            headers=auth_headers(user),
        )

        assert list_response.status_code == 200

        list_body = list_response.json()

        assert list_body["total"] >= 1

        assert any(
            item["id"] == land_requirement_id
            for item in list_body["items"]
        )

    finally:
        if land_requirement_id is not None:
            delete_land_requirement(
                land_requirement_id
            )

        if project_id is not None:
            delete_project(project_id)

        delete_authority(
            authority.id,
            department.id,
        )
        delete_user(user.id)


def test_land_requirement_search():
    user = create_test_user(
        full_name="Land Requirement Search User",
    )

    assign_test_role(
        user_id=user.id,
        role_code="project_director",
    )

    authority, department = create_authority()

    project_id = None
    land_requirement_id = None

    try:
        project_id = create_project(
            user,
            authority.id,
        )

        requirement = create_land_requirement(
            user,
            project_id,
            requirement_reference="LR-SEARCH-UNIQUE",
        )

        land_requirement_id = requirement["id"]

        response = client.get(
            LAND_REQUIREMENT_PATH,
            params={
                "search": "LR-SEARCH-UNIQUE",
            },
            headers=auth_headers(user),
        )

        assert response.status_code == 200

        body = response.json()

        assert body["total"] >= 1

        assert any(
            item["id"] == land_requirement_id
            for item in body["items"]
        )

    finally:
        if land_requirement_id is not None:
            delete_land_requirement(
                land_requirement_id
            )

        if project_id is not None:
            delete_project(project_id)

        delete_authority(
            authority.id,
            department.id,
        )
        delete_user(user.id)


def test_land_requirement_duplicate_reference_returns_409():
    user = create_test_user(
        full_name="Land Requirement Duplicate User",
    )

    assign_test_role(
        user_id=user.id,
        role_code="project_director",
    )

    authority, department = create_authority()

    project_id = None
    first_land_requirement_id = None

    try:
        project_id = create_project(
            user,
            authority.id,
        )

        first_response = client.post(
            LAND_REQUIREMENT_PATH,
            json=land_requirement_payload(
                project_id,
                requirement_reference="LR-DUPLICATE",
            ),
            headers=auth_headers(user),
        )

        assert first_response.status_code == 201

        first_land_requirement_id = (
            first_response.json()["id"]
        )

        second_response = client.post(
            LAND_REQUIREMENT_PATH,
            json=land_requirement_payload(
                project_id,
                requirement_reference="LR-DUPLICATE",
            ),
            headers=auth_headers(user),
        )

        assert second_response.status_code == 409

        assert (
            "already exists"
            in second_response.json()["detail"]
        )

    finally:
        if first_land_requirement_id is not None:
            delete_land_requirement(
                first_land_requirement_id
            )

        if project_id is not None:
            delete_project(project_id)

        delete_authority(
            authority.id,
            department.id,
        )
        delete_user(user.id)


def test_land_requirement_validation_returns_422():
    user = create_test_user(
        full_name="Land Requirement Validation User",
    )

    assign_test_role(
        user_id=user.id,
        role_code="project_director",
    )

    authority, department = create_authority()

    project_id = None

    try:
        project_id = create_project(
            user,
            authority.id,
        )

        response = client.post(
            LAND_REQUIREMENT_PATH,
            json={
                "project_id": project_id,
                "requirement_reference": "",
                "purpose": "Test",
                "required_area_sq_m": -100,
                "state": "Maharashtra",
                "district": "Pune",
                "taluka": "Haveli",
                "village": "Wagholi",
                "description": None,
            },
            headers=auth_headers(user),
        )

        assert response.status_code == 422

    finally:
        if project_id is not None:
            delete_project(project_id)

        delete_authority(
            authority.id,
            department.id,
        )
        delete_user(user.id)


def test_land_requirement_full_approval_lifecycle():
    user = create_test_user(
        full_name="Land Requirement Lifecycle User",
    )

    assign_test_role(
        user_id=user.id,
        role_code="project_director",
    )

    authority, department = create_authority()

    project_id = None
    land_requirement_id = None

    try:
        project_id = create_project(
            user,
            authority.id,
        )

        requirement = create_land_requirement(
            user,
            project_id,
            requirement_reference="LR-LIFECYCLE-001",
        )

        land_requirement_id = requirement["id"]

        submit_response = client.post(
            f"{LAND_REQUIREMENT_PATH}/"
            f"{land_requirement_id}/submit",
            headers=auth_headers(user),
        )

        assert submit_response.status_code == 200
        assert submit_response.json()["status"] == (
            "UNDER_REVIEW"
        )

        approve_response = client.post(
            f"{LAND_REQUIREMENT_PATH}/"
            f"{land_requirement_id}/approve",
            headers=auth_headers(user),
        )

        assert approve_response.status_code == 200
        assert approve_response.json()["status"] == (
            "APPROVED"
        )

        get_response = client.get(
            f"{LAND_REQUIREMENT_PATH}/{land_requirement_id}",
            headers=auth_headers(user),
        )

        assert get_response.status_code == 200
        assert get_response.json()["status"] == "APPROVED"

    finally:
        if land_requirement_id is not None:
            delete_land_requirement(
                land_requirement_id
            )

        if project_id is not None:
            delete_project(project_id)

        delete_authority(
            authority.id,
            department.id,
        )
        delete_user(user.id)


def test_approved_land_requirement_cannot_be_updated():
    user = create_test_user(
        full_name="Land Requirement Approved Update User",
    )

    assign_test_role(
        user_id=user.id,
        role_code="project_director",
    )

    authority, department = create_authority()

    project_id = None
    land_requirement_id = None

    try:
        project_id = create_project(
            user,
            authority.id,
        )

        requirement = create_land_requirement(
            user,
            project_id,
            requirement_reference="LR-APPROVED-001",
        )

        land_requirement_id = requirement["id"]

        submit_response = client.post(
            f"{LAND_REQUIREMENT_PATH}/"
            f"{land_requirement_id}/submit",
            headers=auth_headers(user),
        )

        assert submit_response.status_code == 200

        approve_response = client.post(
            f"{LAND_REQUIREMENT_PATH}/"
            f"{land_requirement_id}/approve",
            headers=auth_headers(user),
        )

        assert approve_response.status_code == 200

        update_response = client.put(
            f"{LAND_REQUIREMENT_PATH}/"
            f"{land_requirement_id}",
            json={
                "requirement_reference": "LR-APPROVED-UPDATED",
                "purpose": "This update must fail",
                "required_area_sq_m": 30000,
                "state": "Maharashtra",
                "district": "Pune",
                "taluka": "Haveli",
                "village": "Wagholi",
                "description": (
                    "Approved requirement must not be edited."
                ),
            },
            headers=auth_headers(user),
        )

        assert update_response.status_code == 400

        assert update_response.json()["detail"] == (
            "Only draft or rejected Land Requirements "
            "can be updated."
        )

    finally:
        if land_requirement_id is not None:
            delete_land_requirement(
                land_requirement_id
            )

        if project_id is not None:
            delete_project(project_id)

        delete_authority(
            authority.id,
            department.id,
        )
        delete_user(user.id)


def test_approved_land_requirement_cannot_be_submitted_again():
    user = create_test_user(
        full_name="Land Requirement Resubmit User",
    )

    assign_test_role(
        user_id=user.id,
        role_code="project_director",
    )

    authority, department = create_authority()

    project_id = None
    land_requirement_id = None

    try:
        project_id = create_project(
            user,
            authority.id,
        )

        requirement = create_land_requirement(
            user,
            project_id,
            requirement_reference="LR-RESUBMIT-001",
        )

        land_requirement_id = requirement["id"]

        submit_response = client.post(
            f"{LAND_REQUIREMENT_PATH}/"
            f"{land_requirement_id}/submit",
            headers=auth_headers(user),
        )

        assert submit_response.status_code == 200

        approve_response = client.post(
            f"{LAND_REQUIREMENT_PATH}/"
            f"{land_requirement_id}/approve",
            headers=auth_headers(user),
        )

        assert approve_response.status_code == 200

        resubmit_response = client.post(
            f"{LAND_REQUIREMENT_PATH}/"
            f"{land_requirement_id}/submit",
            headers=auth_headers(user),
        )

        assert resubmit_response.status_code == 400

        assert resubmit_response.json()["detail"] == (
            "Only draft or rejected Land Requirements "
            "can be submitted."
        )

    finally:
        if land_requirement_id is not None:
            delete_land_requirement(
                land_requirement_id
            )

        if project_id is not None:
            delete_project(project_id)

        delete_authority(
            authority.id,
            department.id,
        )
        delete_user(user.id)


def test_land_requirement_rejection_and_resubmission():
    user = create_test_user(
        full_name="Land Requirement Rejection User",
    )

    assign_test_role(
        user_id=user.id,
        role_code="project_director",
    )

    authority, department = create_authority()

    project_id = None
    land_requirement_id = None

    try:
        project_id = create_project(
            user,
            authority.id,
        )

        requirement = create_land_requirement(
            user,
            project_id,
            requirement_reference="LR-REJECT-001",
        )

        land_requirement_id = requirement["id"]

        submit_response = client.post(
            f"{LAND_REQUIREMENT_PATH}/"
            f"{land_requirement_id}/submit",
            headers=auth_headers(user),
        )

        assert submit_response.status_code == 200
        assert submit_response.json()["status"] == (
            "UNDER_REVIEW"
        )

        reject_response = client.post(
            f"{LAND_REQUIREMENT_PATH}/"
            f"{land_requirement_id}/reject",
            json={
                "reason": "Additional land documentation required.",
            },
            headers=auth_headers(user),
        )

        assert reject_response.status_code == 200
        assert reject_response.json()["status"] == (
            "REJECTED"
        )

        resubmit_response = client.post(
            f"{LAND_REQUIREMENT_PATH}/"
            f"{land_requirement_id}/submit",
            headers=auth_headers(user),
        )

        assert resubmit_response.status_code == 200
        assert resubmit_response.json()["status"] == (
            "UNDER_REVIEW"
        )

    finally:
        if land_requirement_id is not None:
            delete_land_requirement(
                land_requirement_id
            )

        if project_id is not None:
            delete_project(project_id)

        delete_authority(
            authority.id,
            department.id,
        )
        delete_user(user.id)


def test_land_requirement_withdrawal():
    user = create_test_user(
        full_name="Land Requirement Withdrawal User",
    )

    assign_test_role(
        user_id=user.id,
        role_code="project_director",
    )

    authority, department = create_authority()

    project_id = None
    land_requirement_id = None

    try:
        project_id = create_project(
            user,
            authority.id,
        )

        requirement = create_land_requirement(
            user,
            project_id,
            requirement_reference="LR-WITHDRAW-001",
        )

        land_requirement_id = requirement["id"]

        withdraw_response = client.post(
            f"{LAND_REQUIREMENT_PATH}/"
            f"{land_requirement_id}/withdraw",
            json={
                "reason": "Project land requirement withdrawn.",
            },
            headers=auth_headers(user),
        )

        assert withdraw_response.status_code == 200
        assert withdraw_response.json()["status"] == (
            "WITHDRAWN"
        )

    finally:
        if land_requirement_id is not None:
            delete_land_requirement(
                land_requirement_id
            )

        if project_id is not None:
            delete_project(project_id)

        delete_authority(
            authority.id,
            department.id,
        )
        delete_user(user.id)


def test_land_requirement_audit_events_are_recorded():
    user = create_test_user(
        full_name="Land Requirement Audit User",
    )

    assign_test_role(
        user_id=user.id,
        role_code="project_director",
    )

    authority, department = create_authority()

    project_id = None
    land_requirement_id = None

    try:
        project_id = create_project(
            user,
            authority.id,
        )

        requirement = create_land_requirement(
            user,
            project_id,
            requirement_reference="LR-AUDIT-001",
        )

        land_requirement_id = requirement["id"]

        client.post(
            f"{LAND_REQUIREMENT_PATH}/"
            f"{land_requirement_id}/submit",
            headers=auth_headers(user),
        )

        client.post(
            f"{LAND_REQUIREMENT_PATH}/"
            f"{land_requirement_id}/approve",
            headers=auth_headers(user),
        )

        db = SessionLocal()

        try:
            actions = {
                row.action
                for row in db.query(AuditEvent)
                .filter(
                    AuditEvent.entity_type
                    == "land_requirement",
                    AuditEvent.entity_id
                    == land_requirement_id,
                )
                .all()
            }

        finally:
            db.close()

        assert "land_requirement_created" in actions
        assert "land_requirement_submitted" in actions
        assert "land_requirement_approved" in actions

    finally:
        if land_requirement_id is not None:
            delete_land_requirement(
                land_requirement_id
            )

        if project_id is not None:
            delete_project(project_id)

        delete_authority(
            authority.id,
            department.id,
        )
        delete_user(user.id)
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.core.jwt import create_access_token
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.main import app
from app.models.acquisition_case import AcquisitionCase
from app.models.authority import Authority
from app.models.case_parcel import CaseParcel
from app.models.department import Department
from app.models.land_requirement import LandRequirement
from app.models.parcel import Parcel
from app.models.project import Project
from app.models.role import Role
from app.models.survey_record import SurveyRecord
from app.models.user import User
from app.models.user_role import UserRole


client = TestClient(app)

TEST_PASSWORD_HASH = hash_password(
    "AAKAR-Survey-API-Test-Password-123!"
)


def create_test_user(
    db,
    name_prefix: str,
    is_active: bool = True,
):
    suffix = uuid4().hex[:8]

    user = User(
        email=f"{name_prefix.lower().replace(' ', '.')}.{suffix}@example.com",
        password_hash=TEST_PASSWORD_HASH,
        full_name=f"{name_prefix} {suffix}",
        is_active=is_active,
    )

    db.add(user)
    db.flush()

    return user


def get_role(db, role_code: str):
    role = db.query(Role).filter(
        Role.code == role_code,
        Role.is_active.is_(True),
    ).first()

    if role is None:
        raise RuntimeError(
            f"Required role does not exist: {role_code}"
        )

    return role


def assign_role(db, user_id, role_code: str):
    role = get_role(db, role_code)

    existing = db.query(UserRole).filter(
        UserRole.user_id == user_id,
        UserRole.role_id == role.id,
    ).first()

    if existing is None:
        db.add(
            UserRole(
                user_id=user_id,
                role_id=role.id,
            )
        )
        db.flush()

    return role


def create_department(db):
    suffix = uuid4().hex[:8]

    department = Department(
        code=f"DEP-SURVEY-API-{suffix}",
        name=f"Survey API Test Department {suffix}",
        description="Survey API test department",
        is_active=True,
    )

    db.add(department)
    db.flush()

    return department


def create_authority(db, department):
    suffix = uuid4().hex[:8]

    authority = Authority(
        department_id=department.id,
        code=f"AUTH-SURVEY-API-{suffix}",
        name=f"Survey API Test Authority {suffix}",
        authority_type="DISTRICT",
        description="Survey API test authority",
        is_active=True,
    )

    db.add(authority)
    db.flush()

    return authority


def create_project(db, user, authority):
    suffix = uuid4().hex[:8]

    project = Project(
        code=f"PRJ-SURVEY-API-{suffix}",
        name=f"AAKAR Survey API Test Project {suffix}",
        sector="TRANSPORT",
        description="Survey API test project",
        responsible_authority_id=authority.id,
        created_by_user_id=user.id,
        updated_by_user_id=user.id,
        status="DRAFT",
    )

    db.add(project)
    db.flush()

    return project


def create_land_requirement(db, project):
    suffix = uuid4().hex[:8]

    requirement = LandRequirement(
        project_id=project.id,
        requirement_reference=f"REQ-SURVEY-API-{suffix}",
        purpose="Survey API testing land requirement",
        required_area_sq_m=Decimal("2500.0000"),
        state="Maharashtra",
        district="Pune",
        taluka="Haveli",
        village="Wagholi",
        description="Survey API test requirement",
        status="DRAFT",
    )

    db.add(requirement)
    db.flush()

    return requirement


def create_acquisition_case(db, requirement, user, authority):
    suffix = uuid4().hex[:8]

    case = AcquisitionCase(
        land_requirement_id=requirement.id,
        case_number=f"CASE-SURVEY-API-{suffix}",
        legal_framework="RFCTLARR_2013",
        legal_route="RFCTLARR_STANDARD",
        acquisition_method="COMPULSORY_ACQUISITION",
        responsible_authority_id=authority.id,
        assigned_user_id=user.id,
        status="ACTIVE",
        current_stage="INITIATION",
        description="Survey API test acquisition case",
    )

    db.add(case)
    db.flush()

    return case


def create_parcel(db):
    suffix = uuid4().hex[:8]

    parcel = Parcel(
        parcel_reference=f"PAR-SURVEY-API-{suffix}",
        state="Maharashtra",
        district="Pune",
        taluka="Haveli",
        village="Wagholi",
        survey_number=f"500/{suffix}",
        subdivision_number=None,
        recorded_area_sq_m=Decimal("2500.0000"),
        surveyed_area_sq_m=None,
        acquired_area_sq_m=None,
        land_category="AGRICULTURAL",
        land_record_reference=None,
        source_system=None,
        geometry=None,
    )

    db.add(parcel)
    db.flush()

    return parcel


def create_case_parcel_link(db, case, parcel):
    link = CaseParcel(
        acquisition_case_id=case.id,
        parcel_id=parcel.id,
        inclusion_status="ACTIVE",
    )

    db.add(link)
    db.flush()

    return link


def create_token(user):
    return create_access_token(user.id)


def auth_headers(user):
    return {
        "Authorization": f"Bearer {create_token(user)}"
    }


@pytest.fixture()
def survey_api_context():
    db = SessionLocal()

    created_user_ids = []
    created_role_ids = []
    created_project_ids = []
    created_parcel_ids = []
    created_requirement_ids = []
    created_case_ids = []
    created_department_ids = []
    created_authority_ids = []

    try:
        creator = create_test_user(
            db,
            "Survey API Creator",
        )

        surveyor = create_test_user(
            db,
            "Survey API Surveyor",
        )

        verifier = create_test_user(
            db,
            "Survey API Verifier",
        )

        unauthorized = create_test_user(
            db,
            "Survey API Unauthorized",
        )

        inactive_verifier = create_test_user(
            db,
            "Survey API Inactive Verifier",
            is_active=False,
        )

        created_user_ids.extend(
            [
                creator.id,
                surveyor.id,
                verifier.id,
                unauthorized.id,
                inactive_verifier.id,
            ]
        )

        assign_role(
            db,
            creator.id,
            "land_acquisition_officer",
        )

        assign_role(
            db,
            surveyor.id,
            "land_acquisition_officer",
        )

        assign_role(
            db,
            verifier.id,
            "field_verification_officer",
        )

        department = create_department(db)
        created_department_ids.append(department.id)

        authority = create_authority(
            db,
            department,
        )
        created_authority_ids.append(authority.id)

        project = create_project(
            db,
            creator,
            authority,
        )
        created_project_ids.append(project.id)

        requirement = create_land_requirement(
            db,
            project,
        )
        created_requirement_ids.append(requirement.id)

        case = create_acquisition_case(
            db,
            requirement,
            creator,
            authority,
        )
        created_case_ids.append(case.id)

        parcel = create_parcel(db)
        created_parcel_ids.append(parcel.id)

        create_case_parcel_link(
            db,
            case,
            parcel,
        )

        unlinked_parcel = create_parcel(db)
        created_parcel_ids.append(unlinked_parcel.id)

        db.commit()

        yield {
            "db": db,
            "creator": creator,
            "surveyor": surveyor,
            "verifier": verifier,
            "unauthorized": unauthorized,
            "inactive_verifier": inactive_verifier,
            "department": department,
            "authority": authority,
            "project": project,
            "requirement": requirement,
            "case": case,
            "parcel": parcel,
            "unlinked_parcel": unlinked_parcel,
        }

    finally:
        try:
            for case_id in created_case_ids:
                db.execute(
                    delete(SurveyRecord).where(
                        SurveyRecord.acquisition_case_id == case_id
                    )
                )

            if created_case_ids:
                db.execute(
                    delete(CaseParcel).where(
                        CaseParcel.acquisition_case_id.in_(
                            created_case_ids
                        )
                    )
                )

            if created_parcel_ids:
                db.execute(
                    delete(CaseParcel).where(
                        CaseParcel.parcel_id.in_(
                            created_parcel_ids
                        )
                    )
                )

            if created_case_ids:
                db.execute(
                    delete(AcquisitionCase).where(
                        AcquisitionCase.id.in_(
                            created_case_ids
                        )
                    )
                )

            if created_requirement_ids:
                db.execute(
                    delete(LandRequirement).where(
                        LandRequirement.id.in_(
                            created_requirement_ids
                        )
                    )
                )

            if created_project_ids:
                db.execute(
                    delete(Project).where(
                        Project.id.in_(
                            created_project_ids
                        )
                    )
                )

            if created_authority_ids:
                db.execute(
                    delete(Authority).where(
                        Authority.id.in_(
                            created_authority_ids
                        )
                    )
                )

            if created_department_ids:
                db.execute(
                    delete(Department).where(
                        Department.id.in_(
                            created_department_ids
                        )
                    )
                )

            if created_user_ids:
                db.execute(
                    delete(UserRole).where(
                        UserRole.user_id.in_(
                            created_user_ids
                        )
                    )
                )

                db.execute(
                    delete(User).where(
                        User.id.in_(
                            created_user_ids
                        )
                    )
                )

            db.commit()

        except Exception:
            db.rollback()
            raise

        finally:
            db.close()


def create_survey(client, context, reference="SUR-API-001"):
    return client.post(
        "/api/v1/surveys",
        json={
            "acquisition_case_id": str(
                context["case"].id
            ),
            "parcel_id": str(
                context["parcel"].id
            ),
            "survey_reference": reference,
            "survey_type": "PRELIMINARY",
            "survey_method": "FIELD_SURVEY",
            "recorded_area_sq_m": "2500.0000",
            "surveyor_user_id": str(
                context["surveyor"].id
            ),
            "notes": "API survey test",
        },
        headers=auth_headers(
            context["creator"]
        ),
    )


def prepare_survey_for_verification(
    client,
    context,
    reference="SUR-VERIFY-API",
):
    response = create_survey(
        client,
        context,
        reference,
    )

    assert response.status_code == 201, response.text

    survey_id = response.json()["id"]

    response = client.post(
        f"/api/v1/surveys/{survey_id}/start",
        headers=auth_headers(
            context["surveyor"]
        ),
    )

    assert response.status_code == 200, response.text

    response = client.post(
        f"/api/v1/surveys/{survey_id}/complete",
        json={
            "measured_area_sq_m": "2500.0000",
        },
        headers=auth_headers(
            context["surveyor"]
        ),
    )

    assert response.status_code == 200, response.text

    response = client.post(
        f"/api/v1/surveys/{survey_id}/review",
        headers=auth_headers(
            context["surveyor"]
        ),
    )

    assert response.status_code == 200, response.text

    return survey_id


def test_create_survey_api(survey_api_context):
    context = survey_api_context

    response = create_survey(
        client,
        context,
    )

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["survey_reference"] == "SUR-API-001"
    assert data["status"] == "PLANNED"
    assert data["acquisition_case_id"] == str(
        context["case"].id
    )
    assert data["parcel_id"] == str(
        context["parcel"].id
    )
    assert data["recorded_area_sq_m"] == "2500.0000"


def test_get_survey_api(survey_api_context):
    context = survey_api_context

    create_response = create_survey(
        client,
        context,
        "SUR-GET-API",
    )

    assert create_response.status_code == 201

    survey_id = create_response.json()["id"]

    response = client.get(
        f"/api/v1/surveys/{survey_id}",
        headers=auth_headers(
            context["creator"]
        ),
    )

    assert response.status_code == 200, response.text
    assert response.json()["id"] == survey_id


def test_list_surveys_api(survey_api_context):
    context = survey_api_context

    create_response = create_survey(
        client,
        context,
        "SUR-LIST-API",
    )

    assert create_response.status_code == 201

    response = client.get(
        "/api/v1/surveys",
        headers=auth_headers(
            context["creator"]
        ),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert "items" in data
    assert "total" in data
    assert "offset" in data
    assert "limit" in data
    assert data["total"] >= 1


def test_start_survey_api(survey_api_context):
    context = survey_api_context

    create_response = create_survey(
        client,
        context,
        "SUR-START-API",
    )

    assert create_response.status_code == 201

    survey_id = create_response.json()["id"]

    response = client.post(
        f"/api/v1/surveys/{survey_id}/start",
        headers=auth_headers(
            context["surveyor"]
        ),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["status"] == "IN_PROGRESS"
    assert data["surveyor_user_id"] == str(
        context["surveyor"].id
    )


def test_complete_survey_api(survey_api_context):
    context = survey_api_context

    create_response = create_survey(
        client,
        context,
        "SUR-COMPLETE-API",
    )

    assert create_response.status_code == 201

    survey_id = create_response.json()["id"]

    response = client.post(
        f"/api/v1/surveys/{survey_id}/start",
        headers=auth_headers(
            context["surveyor"]
        ),
    )

    assert response.status_code == 200

    response = client.post(
        f"/api/v1/surveys/{survey_id}/complete",
        json={
            "measured_area_sq_m": "2600.0000",
        },
        headers=auth_headers(
            context["surveyor"]
        ),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["status"] == "COMPLETED"
    assert data["measured_area_sq_m"] == "2600.0000"
    assert data["area_difference_sq_m"] == "100.0000"
    assert data["area_difference_percentage"] == "4.000000"
    assert data["conducted_at"] is not None


def test_review_survey_api(survey_api_context):
    context = survey_api_context

    create_response = create_survey(
        client,
        context,
        "SUR-REVIEW-API",
    )

    assert create_response.status_code == 201

    survey_id = create_response.json()["id"]

    response = client.post(
        f"/api/v1/surveys/{survey_id}/start",
        headers=auth_headers(
            context["surveyor"]
        ),
    )

    assert response.status_code == 200

    response = client.post(
        f"/api/v1/surveys/{survey_id}/complete",
        json={
            "measured_area_sq_m": "2505.5000",
        },
        headers=auth_headers(
            context["surveyor"]
        ),
    )

    assert response.status_code == 200

    response = client.post(
        f"/api/v1/surveys/{survey_id}/review",
        headers=auth_headers(
            context["surveyor"]
        ),
    )

    assert response.status_code == 200, response.text

    assert response.json()["status"] == "REQUIRES_REVIEW"


def test_verify_survey_api(survey_api_context):
    context = survey_api_context

    survey_id = prepare_survey_for_verification(
        client,
        context,
        "SUR-VERIFY-API",
    )

    response = client.post(
        f"/api/v1/surveys/{survey_id}/verify",
        headers=auth_headers(
            context["verifier"]
        ),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["status"] == "VERIFIED"
    assert data["verified_by_user_id"] == str(
        context["verifier"].id
    )
    assert data["verified_at"] is not None


def test_cancel_survey_api(survey_api_context):
    context = survey_api_context

    create_response = create_survey(
        client,
        context,
        "SUR-CANCEL-API",
    )

    assert create_response.status_code == 201

    survey_id = create_response.json()["id"]

    response = client.post(
        f"/api/v1/surveys/{survey_id}/cancel",
        headers=auth_headers(
            context["creator"]
        ),
    )

    assert response.status_code == 200, response.text

    assert response.json()["status"] == "CANCELLED"


def test_invalid_status_transition_returns_400(
    survey_api_context,
):
    context = survey_api_context

    create_response = create_survey(
        client,
        context,
        "SUR-INVALID-STATUS-API",
    )

    assert create_response.status_code == 201

    survey_id = create_response.json()["id"]

    response = client.post(
        f"/api/v1/surveys/{survey_id}/review",
        headers=auth_headers(
            context["surveyor"]
        ),
    )

    assert response.status_code == 400, response.text


def test_get_missing_survey_returns_404(
    survey_api_context,
):
    context = survey_api_context

    missing_id = uuid4()

    response = client.get(
        f"/api/v1/surveys/{missing_id}",
        headers=auth_headers(
            context["creator"]
        ),
    )

    assert response.status_code == 404, response.text


def test_create_survey_without_active_case_parcel_returns_400(
    survey_api_context,
):
    context = survey_api_context

    response = client.post(
        "/api/v1/surveys",
        json={
            "acquisition_case_id": str(
                context["case"].id
            ),
            "parcel_id": str(
                context["unlinked_parcel"].id
            ),
            "survey_reference": "SUR-UNLINKED-API",
            "survey_type": "PRELIMINARY",
            "survey_method": "FIELD_SURVEY",
            "recorded_area_sq_m": "2500.0000",
            "surveyor_user_id": str(
                context["surveyor"].id
            ),
        },
        headers=auth_headers(
            context["creator"]
        ),
    )

    assert response.status_code == 400, response.text


def test_create_survey_requires_permission(
    survey_api_context,
):
    context = survey_api_context

    response = client.post(
        "/api/v1/surveys",
        json={
            "acquisition_case_id": str(
                context["case"].id
            ),
            "parcel_id": str(
                context["parcel"].id
            ),
            "survey_reference": "SUR-NO-PERMISSION",
            "survey_type": "PRELIMINARY",
            "survey_method": "FIELD_SURVEY",
            "recorded_area_sq_m": "2500.0000",
        },
        headers=auth_headers(
            context["unauthorized"]
        ),
    )

    assert response.status_code == 403, response.text


def test_verify_requires_verification_permission(
    survey_api_context,
):
    context = survey_api_context

    survey_id = prepare_survey_for_verification(
        client,
        context,
        "SUR-NO-VERIFY-PERM",
    )

    response = client.post(
        f"/api/v1/surveys/{survey_id}/verify",
        headers=auth_headers(
            context["surveyor"]
        ),
    )

    assert response.status_code == 403, response.text


def test_filter_by_status(survey_api_context):
    context = survey_api_context

    create_response = create_survey(
        client,
        context,
        "SUR-FILTER-API",
    )

    assert create_response.status_code == 201

    response = client.get(
        "/api/v1/surveys",
        params={
            "status": "PLANNED",
        },
        headers=auth_headers(
            context["creator"]
        ),
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["total"] >= 1

    for item in data["items"]:
        assert item["status"] == "PLANNED"


def test_invalid_status_filter_returns_400(
    survey_api_context,
):
    context = survey_api_context

    response = client.get(
        "/api/v1/surveys",
        params={
            "status": "INVALID_STATUS",
        },
        headers=auth_headers(
            context["creator"]
        ),
    )

    assert response.status_code == 400, response.text
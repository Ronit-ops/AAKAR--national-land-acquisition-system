from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import delete, select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.acquisition_case import AcquisitionCase
from app.models.audit_event import AuditEvent
from app.models.authority import Authority
from app.models.case_parcel import CaseParcel
from app.models.department import Department
from app.models.land_requirement import LandRequirement
from app.models.parcel import Parcel
from app.models.project import Project
from app.models.survey_record import SurveyRecord
from app.models.user import User
from app.services.survey_service import (
    cancel_survey,
    complete_survey,
    create_survey_record,
    get_survey_record,
    list_survey_records,
    send_survey_for_review,
    start_survey,
    verify_survey,
)


TEST_PASSWORD_HASH = hash_password(
    "AAKAR-Survey-Test-Password-123!"
)


def create_user(
    db,
    *,
    name_prefix: str,
    is_active: bool = True,
) -> User:
    user = User(
        email=f"{name_prefix.lower()}-{uuid4()}@example.com",
        password_hash=TEST_PASSWORD_HASH,
        full_name=name_prefix,
        is_active=is_active,
    )

    db.add(user)
    db.flush()

    return user


def create_department(db) -> Department:
    department = Department(
        code=f"DEPT-SURVEY-{uuid4().hex[:8].upper()}",
        name="AAKAR Survey Test Department",
        description="Department created for survey service tests",
        is_active=True,
    )

    db.add(department)
    db.flush()

    return department


def create_authority(
    db,
    *,
    department: Department,
) -> Authority:
    authority = Authority(
        department_id=department.id,
        code=f"AUTH-SURVEY-{uuid4().hex[:8].upper()}",
        name="AAKAR Survey Test Authority",
        authority_type="DISTRICT",
        description="Authority created for survey service tests",
        is_active=True,
    )

    db.add(authority)
    db.flush()

    return authority


def create_project(
    db,
    *,
    user: User,
    authority: Authority,
) -> Project:
    project = Project(
        code=f"PRJ-SURVEY-{uuid4().hex[:8].upper()}",
        name="AAKAR Survey Test Project",
        sector="TRANSPORT",
        description="Survey service test project",
        responsible_authority_id=authority.id,
        created_by_user_id=user.id,
        updated_by_user_id=user.id,
        status="DRAFT",
    )

    db.add(project)
    db.flush()

    return project


def create_land_requirement(
    db,
    *,
    project: Project,
) -> LandRequirement:
    requirement = LandRequirement(
        project_id=project.id,
        requirement_reference=(
            f"LR-SURVEY-{uuid4().hex[:8].upper()}"
        ),
        purpose="Land required for survey service testing",
        required_area_sq_m=Decimal("10000.0000"),
        state="Maharashtra",
        district="Pune",
        taluka="Haveli",
        village="Wagholi",
        description="Land requirement for survey service tests",
        status="DRAFT",
    )

    db.add(requirement)
    db.flush()

    return requirement


def create_case(
    db,
    *,
    land_requirement: LandRequirement,
) -> AcquisitionCase:
    case = AcquisitionCase(
        land_requirement_id=land_requirement.id,
        case_number=(
            f"AC-SURVEY-{uuid4().hex[:8].upper()}"
        ),
        legal_framework="RFCTLARR_2013",
        legal_route="RFCTLARR_STANDARD",
        acquisition_method="COMPULSORY_ACQUISITION",
        status="ACTIVE",
        current_stage="INITIATION",
        version=1,
    )

    db.add(case)
    db.flush()

    return case


def create_parcel(
    db,
    *,
    user: User,
) -> Parcel:
    parcel = Parcel(
        parcel_reference=(
            f"PAR-SURVEY-{uuid4().hex[:8].upper()}"
        ),
        state="Maharashtra",
        district="Pune",
        taluka="Haveli",
        village="Wagholi",
        survey_number=f"SUR-{uuid4().hex[:6].upper()}",
        subdivision_number="1",
        recorded_area_sq_m=Decimal("2500.0000"),
        surveyed_area_sq_m=None,
        acquired_area_sq_m=None,
        land_category="AGRICULTURAL",
        land_record_reference=(
            f"7/12-SURVEY-{uuid4().hex[:8].upper()}"
        ),
        source_system="SURVEY_TEST",
    )

    db.add(parcel)
    db.flush()

    return parcel


def link_case_parcel(
    db,
    *,
    case: AcquisitionCase,
    parcel: Parcel,
) -> CaseParcel:
    link = CaseParcel(
        acquisition_case_id=case.id,
        parcel_id=parcel.id,
        proposed_area_sq_m=Decimal("2500.0000"),
        inclusion_status="ACTIVE",
    )

    db.add(link)
    db.flush()

    return link


def cleanup(
    db,
    *,
    user_ids: list,
    department_ids: list,
    authority_ids: list,
    project_ids: list,
    parcel_ids: list,
    requirement_ids: list,
    case_ids: list,
) -> None:
    survey_ids = list(
        db.scalars(
            select(SurveyRecord.id).where(
                SurveyRecord.acquisition_case_id.in_(case_ids)
            )
        ).all()
    )

    if survey_ids:
        db.execute(
            delete(AuditEvent).where(
                AuditEvent.entity_type == "survey_record",
                AuditEvent.entity_id.in_(survey_ids),
            )
        )

        db.execute(
            delete(SurveyRecord).where(
                SurveyRecord.id.in_(survey_ids)
            )
        )

    if case_ids:
        db.execute(
            delete(CaseParcel).where(
                CaseParcel.acquisition_case_id.in_(case_ids)
            )
        )

        db.execute(
            delete(AuditEvent).where(
                AuditEvent.entity_type == "acquisition_case",
                AuditEvent.entity_id.in_(case_ids),
            )
        )

        db.execute(
            delete(AcquisitionCase).where(
                AcquisitionCase.id.in_(case_ids)
            )
        )

    if parcel_ids:
        db.execute(
            delete(Parcel).where(
                Parcel.id.in_(parcel_ids)
            )
        )

    if requirement_ids:
        db.execute(
            delete(LandRequirement).where(
                LandRequirement.id.in_(requirement_ids)
            )
        )

    if project_ids:
        db.execute(
            delete(Project).where(
                Project.id.in_(project_ids)
            )
        )

    if authority_ids:
        db.execute(
            delete(Authority).where(
                Authority.id.in_(authority_ids)
            )
        )

    if department_ids:
        db.execute(
            delete(Department).where(
                Department.id.in_(department_ids)
            )
        )

    if user_ids:
        db.execute(
            delete(AuditEvent).where(
                AuditEvent.actor_user_id.in_(user_ids)
            )
        )

        db.execute(
            delete(User).where(
                User.id.in_(user_ids)
            )
        )

    db.commit()


@pytest.fixture
def survey_context():
    db = SessionLocal()

    created_user_ids = []
    created_department_ids = []
    created_authority_ids = []
    created_project_ids = []
    created_parcel_ids = []
    created_requirement_ids = []
    created_case_ids = []

    try:
        creator = create_user(
            db,
            name_prefix="Survey Creator",
        )

        surveyor = create_user(
            db,
            name_prefix="Surveyor",
        )

        verifier = create_user(
            db,
            name_prefix="Survey Verifier",
        )

        inactive_verifier = create_user(
            db,
            name_prefix="Inactive Verifier",
            is_active=False,
        )

        created_user_ids.extend(
            [
                creator.id,
                surveyor.id,
                verifier.id,
                inactive_verifier.id,
            ]
        )

        department = create_department(db)
        created_department_ids.append(department.id)

        authority = create_authority(
            db,
            department=department,
        )
        created_authority_ids.append(authority.id)

        project = create_project(
            db,
            user=creator,
            authority=authority,
        )
        created_project_ids.append(project.id)

        requirement = create_land_requirement(
            db,
            project=project,
        )
        created_requirement_ids.append(requirement.id)

        case = create_case(
            db,
            land_requirement=requirement,
        )
        created_case_ids.append(case.id)

        parcel = create_parcel(
            db,
            user=creator,
        )
        created_parcel_ids.append(parcel.id)

        link_case_parcel(
            db,
            case=case,
            parcel=parcel,
        )

        unlinked_parcel = create_parcel(
            db,
            user=creator,
        )
        created_parcel_ids.append(unlinked_parcel.id)

        db.commit()

        yield {
            "db": db,
            "creator": creator,
            "surveyor": surveyor,
            "verifier": verifier,
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
            cleanup(
                db,
                user_ids=created_user_ids,
                department_ids=created_department_ids,
                authority_ids=created_authority_ids,
                project_ids=created_project_ids,
                parcel_ids=created_parcel_ids,
                requirement_ids=created_requirement_ids,
                case_ids=created_case_ids,
            )
        finally:
            db.close()


def test_create_survey_record(survey_context):
    context = survey_context
    db = context["db"]

    survey = create_survey_record(
        db,
        acquisition_case_id=context["case"].id,
        parcel_id=context["parcel"].id,
        survey_reference="SUR-001",
        survey_type="PRELIMINARY",
        survey_method="FIELD_SURVEY",
        surveyor_user_id=context["surveyor"].id,
        actor_user_id=context["creator"].id,
    )

    assert survey.id is not None
    assert survey.status == "PLANNED"
    assert survey.recorded_area_sq_m == Decimal("2500.0000")
    assert survey.measured_area_sq_m is None
    assert survey.area_difference_sq_m is None
    assert survey.area_difference_percentage is None


def test_create_survey_requires_case_parcel_link(
    survey_context,
):
    context = survey_context
    db = context["db"]

    with pytest.raises(
        ValueError,
        match="not actively associated",
    ):
        create_survey_record(
            db,
            acquisition_case_id=context["case"].id,
            parcel_id=context["unlinked_parcel"].id,
            survey_reference="SUR-UNLINKED",
            survey_type="PRELIMINARY",
            survey_method="FIELD_SURVEY",
            actor_user_id=context["creator"].id,
        )


def test_duplicate_survey_reference_is_rejected(
    survey_context,
):
    context = survey_context
    db = context["db"]

    create_survey_record(
        db,
        acquisition_case_id=context["case"].id,
        parcel_id=context["parcel"].id,
        survey_reference="SUR-DUPLICATE",
        survey_type="PRELIMINARY",
        survey_method="FIELD_SURVEY",
        actor_user_id=context["creator"].id,
    )

    with pytest.raises(
        ValueError,
        match="already exists",
    ):
        create_survey_record(
            db,
            acquisition_case_id=context["case"].id,
            parcel_id=context["parcel"].id,
            survey_reference="SUR-DUPLICATE",
            survey_type="PRELIMINARY",
            survey_method="FIELD_SURVEY",
            actor_user_id=context["creator"].id,
        )


def test_start_survey_assigns_actor_as_surveyor(
    survey_context,
):
    context = survey_context
    db = context["db"]

    survey = create_survey_record(
        db,
        acquisition_case_id=context["case"].id,
        parcel_id=context["parcel"].id,
        survey_reference="SUR-START",
        survey_type="PRELIMINARY",
        survey_method="GNSS",
        actor_user_id=context["creator"].id,
    )

    started = start_survey(
        db,
        survey_id=survey.id,
        actor_user_id=context["surveyor"].id,
    )

    assert started.status == "IN_PROGRESS"
    assert started.surveyor_user_id == context["surveyor"].id


def test_complete_survey_calculates_area_difference(
    survey_context,
):
    context = survey_context
    db = context["db"]

    survey = create_survey_record(
        db,
        acquisition_case_id=context["case"].id,
        parcel_id=context["parcel"].id,
        survey_reference="SUR-COMPLETE",
        survey_type="JOINT_MEASUREMENT",
        survey_method="TOTAL_STATION",
        surveyor_user_id=context["surveyor"].id,
        actor_user_id=context["creator"].id,
    )

    start_survey(
        db,
        survey_id=survey.id,
        actor_user_id=context["surveyor"].id,
    )

    completed = complete_survey(
        db,
        survey_id=survey.id,
        measured_area_sq_m=Decimal("2600.0000"),
        actor_user_id=context["surveyor"].id,
    )

    assert completed.status == "COMPLETED"
    assert completed.measured_area_sq_m == Decimal("2600.0000")
    assert completed.area_difference_sq_m == Decimal("100.0000")
    assert completed.area_difference_percentage == Decimal("4.000000")
    assert completed.conducted_at is not None


def test_negative_area_difference_is_supported(
    survey_context,
):
    context = survey_context
    db = context["db"]

    survey = create_survey_record(
        db,
        acquisition_case_id=context["case"].id,
        parcel_id=context["parcel"].id,
        survey_reference="SUR-NEGATIVE",
        survey_type="RE_MEASUREMENT",
        survey_method="GNSS",
        surveyor_user_id=context["surveyor"].id,
        actor_user_id=context["creator"].id,
    )

    start_survey(
        db,
        survey_id=survey.id,
        actor_user_id=context["surveyor"].id,
    )

    completed = complete_survey(
        db,
        survey_id=survey.id,
        measured_area_sq_m=Decimal("2400.0000"),
        actor_user_id=context["surveyor"].id,
    )

    assert completed.area_difference_sq_m == Decimal("-100.0000")
    assert completed.area_difference_percentage == Decimal("-4.000000")


def test_zero_measured_area_is_rejected(
    survey_context,
):
    context = survey_context
    db = context["db"]

    survey = create_survey_record(
        db,
        acquisition_case_id=context["case"].id,
        parcel_id=context["parcel"].id,
        survey_reference="SUR-ZERO",
        survey_type="PRELIMINARY",
        survey_method="GPS",
        surveyor_user_id=context["surveyor"].id,
        actor_user_id=context["creator"].id,
    )

    start_survey(
        db,
        survey_id=survey.id,
        actor_user_id=context["surveyor"].id,
    )

    with pytest.raises(
        ValueError,
        match="greater than zero",
    ):
        complete_survey(
            db,
            survey_id=survey.id,
            measured_area_sq_m=Decimal("0"),
            actor_user_id=context["surveyor"].id,
        )


def test_completed_survey_can_be_sent_for_review(
    survey_context,
):
    context = survey_context
    db = context["db"]

    survey = create_survey_record(
        db,
        acquisition_case_id=context["case"].id,
        parcel_id=context["parcel"].id,
        survey_reference="SUR-REVIEW",
        survey_type="JOINT_MEASUREMENT",
        survey_method="FIELD_SURVEY",
        surveyor_user_id=context["surveyor"].id,
        actor_user_id=context["creator"].id,
    )

    start_survey(
        db,
        survey_id=survey.id,
        actor_user_id=context["surveyor"].id,
    )

    complete_survey(
        db,
        survey_id=survey.id,
        measured_area_sq_m=Decimal("2505.5000"),
        actor_user_id=context["surveyor"].id,
    )

    reviewed = send_survey_for_review(
        db,
        survey_id=survey.id,
        actor_user_id=context["surveyor"].id,
    )

    assert reviewed.status == "REQUIRES_REVIEW"


def test_survey_can_be_verified(
    survey_context,
):
    context = survey_context
    db = context["db"]

    survey = create_survey_record(
        db,
        acquisition_case_id=context["case"].id,
        parcel_id=context["parcel"].id,
        survey_reference="SUR-VERIFY",
        survey_type="BOUNDARY_VERIFICATION",
        survey_method="GNSS",
        surveyor_user_id=context["surveyor"].id,
        actor_user_id=context["creator"].id,
    )

    start_survey(
        db,
        survey_id=survey.id,
        actor_user_id=context["surveyor"].id,
    )

    complete_survey(
        db,
        survey_id=survey.id,
        measured_area_sq_m=Decimal("2500.2500"),
        actor_user_id=context["surveyor"].id,
    )

    send_survey_for_review(
        db,
        survey_id=survey.id,
        actor_user_id=context["surveyor"].id,
    )

    verified = verify_survey(
        db,
        survey_id=survey.id,
        verifier_user_id=context["verifier"].id,
        actor_user_id=context["verifier"].id,
    )

    assert verified.status == "VERIFIED"
    assert verified.verified_by_user_id == context["verifier"].id
    assert verified.verified_at is not None


def test_inactive_verifier_is_rejected(
    survey_context,
):
    context = survey_context
    db = context["db"]

    survey = create_survey_record(
        db,
        acquisition_case_id=context["case"].id,
        parcel_id=context["parcel"].id,
        survey_reference="SUR-INACTIVE",
        survey_type="PRELIMINARY",
        survey_method="GPS",
        surveyor_user_id=context["surveyor"].id,
        actor_user_id=context["creator"].id,
    )

    start_survey(
        db,
        survey_id=survey.id,
        actor_user_id=context["surveyor"].id,
    )

    complete_survey(
        db,
        survey_id=survey.id,
        measured_area_sq_m=Decimal("2500.0000"),
        actor_user_id=context["surveyor"].id,
    )

    send_survey_for_review(
        db,
        survey_id=survey.id,
        actor_user_id=context["surveyor"].id,
    )

    with pytest.raises(
        ValueError,
        match="inactive",
    ):
        verify_survey(
            db,
            survey_id=survey.id,
            verifier_user_id=context["inactive_verifier"].id,
            actor_user_id=context["inactive_verifier"].id,
        )


def test_invalid_status_transition_is_rejected(
    survey_context,
):
    context = survey_context
    db = context["db"]

    survey = create_survey_record(
        db,
        acquisition_case_id=context["case"].id,
        parcel_id=context["parcel"].id,
        survey_reference="SUR-INVALID",
        survey_type="PRELIMINARY",
        survey_method="FIELD_SURVEY",
        actor_user_id=context["creator"].id,
    )

    with pytest.raises(
        ValueError,
        match="Invalid survey status transition",
    ):
        verify_survey(
            db,
            survey_id=survey.id,
            verifier_user_id=context["verifier"].id,
            actor_user_id=context["verifier"].id,
        )


def test_cancel_planned_survey(
    survey_context,
):
    context = survey_context
    db = context["db"]

    survey = create_survey_record(
        db,
        acquisition_case_id=context["case"].id,
        parcel_id=context["parcel"].id,
        survey_reference="SUR-CANCEL",
        survey_type="OTHER",
        survey_method="OTHER",
        actor_user_id=context["creator"].id,
    )

    cancelled = cancel_survey(
        db,
        survey_id=survey.id,
        actor_user_id=context["creator"].id,
    )

    assert cancelled.status == "CANCELLED"


def test_cancelled_survey_cannot_restart(
    survey_context,
):
    context = survey_context
    db = context["db"]

    survey = create_survey_record(
        db,
        acquisition_case_id=context["case"].id,
        parcel_id=context["parcel"].id,
        survey_reference="SUR-CANCEL-RESTART",
        survey_type="OTHER",
        survey_method="OTHER",
        actor_user_id=context["creator"].id,
    )

    cancel_survey(
        db,
        survey_id=survey.id,
        actor_user_id=context["creator"].id,
    )

    with pytest.raises(
        ValueError,
        match="Invalid survey status transition",
    ):
        start_survey(
            db,
            survey_id=survey.id,
            actor_user_id=context["surveyor"].id,
        )


def test_verified_survey_cannot_be_verified_again(
    survey_context,
):
    context = survey_context
    db = context["db"]

    survey = create_survey_record(
        db,
        acquisition_case_id=context["case"].id,
        parcel_id=context["parcel"].id,
        survey_reference="SUR-VERIFY-TWICE",
        survey_type="PRELIMINARY",
        survey_method="GNSS",
        surveyor_user_id=context["surveyor"].id,
        actor_user_id=context["creator"].id,
    )

    start_survey(
        db,
        survey_id=survey.id,
        actor_user_id=context["surveyor"].id,
    )

    complete_survey(
        db,
        survey_id=survey.id,
        measured_area_sq_m=Decimal("2500.0000"),
        actor_user_id=context["surveyor"].id,
    )

    send_survey_for_review(
        db,
        survey_id=survey.id,
        actor_user_id=context["surveyor"].id,
    )

    verify_survey(
        db,
        survey_id=survey.id,
        verifier_user_id=context["verifier"].id,
        actor_user_id=context["verifier"].id,
    )

    with pytest.raises(
        ValueError,
        match="Invalid survey status transition",
    ):
        verify_survey(
            db,
            survey_id=survey.id,
            verifier_user_id=context["verifier"].id,
            actor_user_id=context["verifier"].id,
        )


def test_get_and_list_survey_records(
    survey_context,
):
    context = survey_context
    db = context["db"]

    survey = create_survey_record(
        db,
        acquisition_case_id=context["case"].id,
        parcel_id=context["parcel"].id,
        survey_reference="SUR-LIST",
        survey_type="PRELIMINARY",
        survey_method="FIELD_SURVEY",
        actor_user_id=context["creator"].id,
    )

    fetched = get_survey_record(
        db,
        survey.id,
    )

    assert fetched is not None
    assert fetched.id == survey.id

    records = list_survey_records(
        db,
        acquisition_case_id=context["case"].id,
    )

    assert any(
        record.id == survey.id
        for record in records
    )


def test_audit_events_are_created(
    survey_context,
):
    context = survey_context
    db = context["db"]

    survey = create_survey_record(
        db,
        acquisition_case_id=context["case"].id,
        parcel_id=context["parcel"].id,
        survey_reference="SUR-AUDIT",
        survey_type="PRELIMINARY",
        survey_method="FIELD_SURVEY",
        actor_user_id=context["creator"].id,
    )

    events = list(
        db.scalars(
            select(AuditEvent).where(
                AuditEvent.entity_type == "survey_record",
                AuditEvent.entity_id == survey.id,
            )
        ).all()
    )

    assert any(
        event.action == "survey_record_created"
        for event in events
    )
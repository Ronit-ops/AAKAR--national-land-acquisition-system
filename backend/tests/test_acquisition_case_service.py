from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.acquisition_case import (
    AcquisitionCase,
    AcquisitionCaseStageHistory,
)
from app.models.audit_event import AuditEvent
from app.models.authority import Authority
from app.models.department import Department
from app.models.land_requirement import LandRequirement
from app.models.project import Project
from app.models.user import User
from app.services.acquisition_case_service import (
    activate_acquisition_case,
    cancel_acquisition_case,
    close_acquisition_case,
    create_acquisition_case,
    hold_acquisition_case,
    resume_acquisition_case,
    transition_acquisition_case_stage,
    update_acquisition_case,
)
from app.services.land_requirement_service import create_land_requirement
from app.services.project_service import create_project


def create_test_user(db, *, email: str | None = None):
    user = User(
        id=uuid4(),
        email=email or f"acq-case-{uuid4().hex[:10]}@example.com",
        password_hash=hash_password("TestPassword123!"),
        full_name="Acquisition Case Test User",
        is_active=True,
    )

    db.add(user)
    db.flush()

    return user


def create_test_department(db):
    department = Department(
        id=uuid4(),
        code=f"ACQ{uuid4().hex[:8].upper()}",
        name=f"Acquisition Test Department {uuid4().hex[:8]}",
        is_active=True,
    )

    db.add(department)
    db.flush()

    return department


def create_test_authority(db, department_id):
    authority = Authority(
        id=uuid4(),
        department_id=department_id,
        code=f"AUTH{uuid4().hex[:8].upper()}",
        name=f"Acquisition Test Authority {uuid4().hex[:8]}",
        authority_type="DISTRICT_AUTHORITY",
        is_active=True,
    )

    db.add(authority)
    db.flush()

    return authority


def create_test_project(db, *, user_id):
    department = create_test_department(db)

    authority = create_test_authority(
        db,
        department.id,
    )

    project = create_project(
        db,
        code=f"PRJ-{uuid4().hex[:8].upper()}",
        name=f"Acquisition Case Test Project {uuid4().hex[:8]}",
        sector="INFRASTRUCTURE",
        description="Project used for acquisition case service tests.",
        responsible_authority_id=authority.id,
        boundary=None,
        actor_user_id=user_id,
    )

    return project, department, authority


def create_test_land_requirement(
    db,
    *,
    project_id,
    user_id,
    approved: bool = True,
):
    requirement = create_land_requirement(
        db,
        project_id=project_id,
        requirement_reference=f"LR-{uuid4().hex[:8].upper()}",
        purpose="Land requirement for acquisition case service testing.",
        required_area_sq_m=Decimal("10000"),
        state="Maharashtra",
        district="Pune",
        taluka="Haveli",
        village="Wagholi",
        description="Test land requirement.",
        actor_user_id=user_id,
    )

    if approved:
        requirement.status = "APPROVED"
        db.flush()

    return requirement


def create_approved_land_requirement(
    db,
    *,
    user_id,
):
    project, department, authority = create_test_project(
        db,
        user_id=user_id,
    )

    requirement = create_test_land_requirement(
        db,
        project_id=project.id,
        user_id=user_id,
        approved=True,
    )

    db.commit()
    db.refresh(requirement)

    return project, requirement, authority, department


def cleanup_acquisition_case_tree(
    db,
    *,
    case_id=None,
    land_requirement_id=None,
    project_id=None,
    authority_id=None,
    department_id=None,
    user_id=None,
):
    """
    Delete test data in dependency-safe order.

    Projects reference their creator through created_by_user_id,
    so projects must be deleted before users.
    """

    try:
        if case_id is not None:
            db.query(AuditEvent).filter(
                AuditEvent.entity_id == case_id
            ).delete(
                synchronize_session=False
            )

            db.query(AcquisitionCaseStageHistory).filter(
                AcquisitionCaseStageHistory.acquisition_case_id
                == case_id
            ).delete(
                synchronize_session=False
            )

            db.query(AcquisitionCase).filter(
                AcquisitionCase.id == case_id
            ).delete(
                synchronize_session=False
            )

        if land_requirement_id is not None:
            db.query(LandRequirement).filter(
                LandRequirement.id == land_requirement_id
            ).delete(
                synchronize_session=False
            )

        if project_id is not None:
            db.query(Project).filter(
                Project.id == project_id
            ).delete(
                synchronize_session=False
            )

        if authority_id is not None:
            db.query(Authority).filter(
                Authority.id == authority_id
            ).delete(
                synchronize_session=False
            )

        if department_id is not None:
            db.query(Department).filter(
                Department.id == department_id
            ).delete(
                synchronize_session=False
            )

        if user_id is not None:
            db.query(User).filter(
                User.id == user_id
            ).delete(
                synchronize_session=False
            )

        db.commit()

    except Exception:
        db.rollback()
        raise


def create_case(
    db,
    *,
    requirement_id,
    authority_id,
    user_id,
    case_number=None,
):
    return create_acquisition_case(
        db,
        land_requirement_id=requirement_id,
        case_number=case_number or f"ACQ-{uuid4().hex[:8].upper()}",
        legal_framework="RFCTLARR_2013",
        legal_route="RFCTLARR_STANDARD",
        acquisition_method="COMPULSORY_ACQUISITION",
        responsible_authority_id=authority_id,
        assigned_user_id=user_id,
        description="Test acquisition case.",
        actor_user_id=user_id,
    )


def test_create_acquisition_case():
    db = SessionLocal()

    user = create_test_user(db)

    project = None
    requirement = None
    authority = None
    department = None
    case = None

    try:
        (
            project,
            requirement,
            authority,
            department,
        ) = create_approved_land_requirement(
            db,
            user_id=user.id,
        )

        case = create_case(
            db,
            requirement_id=requirement.id,
            authority_id=authority.id,
            user_id=user.id,
        )

        assert case.id is not None
        assert case.land_requirement_id == requirement.id
        assert case.status == "DRAFT"
        assert case.current_stage == "INITIATION"
        assert case.version == 1
        assert case.legal_framework == "RFCTLARR_2013"
        assert case.legal_route == "RFCTLARR_STANDARD"
        assert case.acquisition_method == "COMPULSORY_ACQUISITION"

        audit = db.execute(
            select(AuditEvent).where(
                AuditEvent.entity_id == case.id
            )
        ).scalars().all()

        assert audit

    finally:
        cleanup_acquisition_case_tree(
            db,
            case_id=case.id if case else None,
            land_requirement_id=requirement.id if requirement else None,
            project_id=project.id if project else None,
            authority_id=authority.id if authority else None,
            department_id=department.id if department else None,
            user_id=user.id,
        )

        db.close()


def test_create_acquisition_case_requires_approved_land_requirement():
    db = SessionLocal()

    user = create_test_user(db)

    project = None
    requirement = None
    authority = None
    department = None

    try:
        project, department, authority = create_test_project(
            db,
            user_id=user.id,
        )

        requirement = create_test_land_requirement(
            db,
            project_id=project.id,
            user_id=user.id,
            approved=False,
        )

        db.commit()

        with pytest.raises(ValueError, match="approved"):
            create_case(
                db,
                requirement_id=requirement.id,
                authority_id=authority.id,
                user_id=user.id,
            )

    finally:
        cleanup_acquisition_case_tree(
            db,
            land_requirement_id=requirement.id if requirement else None,
            project_id=project.id if project else None,
            authority_id=authority.id if authority else None,
            department_id=department.id if department else None,
            user_id=user.id,
        )

        db.close()


def test_duplicate_acquisition_case_number_is_rejected():
    db = SessionLocal()

    user = create_test_user(db)

    project = None
    requirement = None
    authority = None
    department = None
    first_case = None

    try:
        (
            project,
            requirement,
            authority,
            department,
        ) = create_approved_land_requirement(
            db,
            user_id=user.id,
        )

        case_number = f"ACQ-{uuid4().hex[:8].upper()}"

        first_case = create_case(
            db,
            requirement_id=requirement.id,
            authority_id=authority.id,
            user_id=user.id,
            case_number=case_number,
        )

        with pytest.raises(ValueError, match="case number"):
            create_case(
                db,
                requirement_id=requirement.id,
                authority_id=authority.id,
                user_id=user.id,
                case_number=case_number,
            )

    finally:
        cleanup_acquisition_case_tree(
            db,
            case_id=first_case.id if first_case else None,
            land_requirement_id=requirement.id if requirement else None,
            project_id=project.id if project else None,
            authority_id=authority.id if authority else None,
            department_id=department.id if department else None,
            user_id=user.id,
        )

        db.close()


def test_update_acquisition_case_uses_optimistic_concurrency():
    db = SessionLocal()

    user = create_test_user(db)

    project = None
    requirement = None
    authority = None
    department = None
    case = None

    try:
        (
            project,
            requirement,
            authority,
            department,
        ) = create_approved_land_requirement(
            db,
            user_id=user.id,
        )

        case = create_case(
            db,
            requirement_id=requirement.id,
            authority_id=authority.id,
            user_id=user.id,
        )

        updated_case = update_acquisition_case(
            db,
            acquisition_case_id=case.id,
            actor_user_id=user.id,
            expected_version=1,
            update_fields={"description"},
            description="Updated acquisition case description.",
        )

        assert updated_case.version == 2
        assert (
            updated_case.description
            == "Updated acquisition case description."
        )

        with pytest.raises(
    ValueError,
    match="modified by another user",
):
            update_acquisition_case(
                db,
                acquisition_case_id=case.id,
                actor_user_id=user.id,
                expected_version=1,
                update_fields={"description"},
                description="Stale update.",
            )

    finally:
        cleanup_acquisition_case_tree(
            db,
            case_id=case.id if case else None,
            land_requirement_id=requirement.id if requirement else None,
            project_id=project.id if project else None,
            authority_id=authority.id if authority else None,
            department_id=department.id if department else None,
            user_id=user.id,
        )

        db.close()


def test_acquisition_case_lifecycle():
    db = SessionLocal()

    user = create_test_user(db)

    project = None
    requirement = None
    authority = None
    department = None
    case = None

    try:
        (
            project,
            requirement,
            authority,
            department,
        ) = create_approved_land_requirement(
            db,
            user_id=user.id,
        )

        case = create_case(
            db,
            requirement_id=requirement.id,
            authority_id=authority.id,
            user_id=user.id,
        )

        case = activate_acquisition_case(
            db,
            acquisition_case_id=case.id,
            actor_user_id=user.id,
            expected_version=1,
        )

        assert case.status == "ACTIVE"
        assert case.version == 2
        assert case.opened_at is not None

        case = hold_acquisition_case(
            db,
            acquisition_case_id=case.id,
            actor_user_id=user.id,
            expected_version=2,
            reason="Temporary administrative hold.",
        )

        assert case.status == "ON_HOLD"
        assert case.version == 3

        case = resume_acquisition_case(
            db,
            acquisition_case_id=case.id,
            actor_user_id=user.id,
            expected_version=3,
        )

        assert case.status == "ACTIVE"
        assert case.version == 4

        case = cancel_acquisition_case(
            db,
            acquisition_case_id=case.id,
            actor_user_id=user.id,
            expected_version=4,
            reason="Test cancellation.",
        )

        assert case.status == "CANCELLED"
        assert case.version == 5
        assert case.closed_at is not None

    finally:
        cleanup_acquisition_case_tree(
            db,
            case_id=case.id if case else None,
            land_requirement_id=requirement.id if requirement else None,
            project_id=project.id if project else None,
            authority_id=authority.id if authority else None,
            department_id=department.id if department else None,
            user_id=user.id,
        )

        db.close()


def test_invalid_stage_transition_is_rejected():
    db = SessionLocal()

    user = create_test_user(db)

    project = None
    requirement = None
    authority = None
    department = None
    case = None

    try:
        (
            project,
            requirement,
            authority,
            department,
        ) = create_approved_land_requirement(
            db,
            user_id=user.id,
        )

        case = create_case(
            db,
            requirement_id=requirement.id,
            authority_id=authority.id,
            user_id=user.id,
        )

        case = activate_acquisition_case(
            db,
            acquisition_case_id=case.id,
            actor_user_id=user.id,
            expected_version=1,
        )

        with pytest.raises(ValueError, match="transition"):
            transition_acquisition_case_stage(
                db,
                acquisition_case_id=case.id,
                actor_user_id=user.id,
                to_stage="AWARD",
                expected_version=2,
                reason="Invalid direct transition.",
            )

    finally:
        cleanup_acquisition_case_tree(
            db,
            case_id=case.id if case else None,
            land_requirement_id=requirement.id if requirement else None,
            project_id=project.id if project else None,
            authority_id=authority.id if authority else None,
            department_id=department.id if department else None,
            user_id=user.id,
        )

        db.close()


def test_stage_transition_creates_history():
    db = SessionLocal()

    user = create_test_user(db)

    project = None
    requirement = None
    authority = None
    department = None
    case = None

    try:
        (
            project,
            requirement,
            authority,
            department,
        ) = create_approved_land_requirement(
            db,
            user_id=user.id,
        )

        case = create_case(
            db,
            requirement_id=requirement.id,
            authority_id=authority.id,
            user_id=user.id,
        )

        case = activate_acquisition_case(
            db,
            acquisition_case_id=case.id,
            actor_user_id=user.id,
            expected_version=1,
        )

        case = transition_acquisition_case_stage(
            db,
            acquisition_case_id=case.id,
            actor_user_id=user.id,
            to_stage="PRELIMINARY_NOTIFICATION",
            expected_version=2,
            reason="SIA not required for this test route.",
        )

        assert case.current_stage == "PRELIMINARY_NOTIFICATION"
        assert case.version == 3

        history = db.execute(
            select(AcquisitionCaseStageHistory)
            .where(
                AcquisitionCaseStageHistory.acquisition_case_id
                == case.id
            )
            .order_by(
                AcquisitionCaseStageHistory.changed_at.asc()
            )
        ).scalars().all()

        assert len(history) == 1
        assert history[0].from_stage == "INITIATION"
        assert history[0].to_stage == "PRELIMINARY_NOTIFICATION"
        assert (
            history[0].reason
            == "SIA not required for this test route."
        )
        assert history[0].changed_by_user_id == user.id

    finally:
        cleanup_acquisition_case_tree(
            db,
            case_id=case.id if case else None,
            land_requirement_id=requirement.id if requirement else None,
            project_id=project.id if project else None,
            authority_id=authority.id if authority else None,
            department_id=department.id if department else None,
            user_id=user.id,
        )

        db.close()


def test_close_requires_handover_stage():
    db = SessionLocal()

    user = create_test_user(db)

    project = None
    requirement = None
    authority = None
    department = None
    case = None

    try:
        (
            project,
            requirement,
            authority,
            department,
        ) = create_approved_land_requirement(
            db,
            user_id=user.id,
        )

        case = create_case(
            db,
            requirement_id=requirement.id,
            authority_id=authority.id,
            user_id=user.id,
        )

        case = activate_acquisition_case(
            db,
            acquisition_case_id=case.id,
            actor_user_id=user.id,
            expected_version=1,
        )

        with pytest.raises(ValueError, match="HANDOVER"):
            close_acquisition_case(
                db,
                acquisition_case_id=case.id,
                actor_user_id=user.id,
                expected_version=2,
            )

    finally:
        cleanup_acquisition_case_tree(
            db,
            case_id=case.id if case else None,
            land_requirement_id=requirement.id if requirement else None,
            project_id=project.id if project else None,
            authority_id=authority.id if authority else None,
            department_id=department.id if department else None,
            user_id=user.id,
        )

        db.close()
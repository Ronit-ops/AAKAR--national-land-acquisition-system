from uuid import uuid4

import pytest

from app.db.session import SessionLocal
from app.models.authority import Authority
from app.models.department import Department
from app.services.authority_service import (
    VALID_AUTHORITY_TYPES,
    create_authority,
    get_authority,
    list_authorities,
    set_authority_active_status,
    update_authority,
)
from app.services.department_service import create_department


TEST_PREFIX = "AUTH-TEST"


def create_test_department(
    *,
    code: str | None = None,
    name: str = "Test Department",
    is_active: bool = True,
) -> Department:
    db = SessionLocal()

    try:
        department = create_department(
            db=db,
            code=code or f"DPT-{uuid4().hex[:8].upper()}",
            name=name,
            description="Test department",
        )

        if not is_active:
            department.is_active = False
            db.commit()
            db.refresh(department)

        return department
    finally:
        db.close()


def create_test_authority(
    *,
    department_id,
    code: str | None = None,
    name: str = "Test Authority",
    authority_type: str = "STATE",
) -> Authority:
    db = SessionLocal()

    try:
        return create_authority(
            db=db,
            department_id=department_id,
            code=code or f"{TEST_PREFIX}-{uuid4().hex[:8].upper()}",
            name=name,
            authority_type=authority_type,
            description="Test authority",
        )
    finally:
        db.close()


def delete_test_authority(authority_id) -> None:
    db = SessionLocal()

    try:
        authority = db.get(Authority, authority_id)

        if authority is not None:
            db.delete(authority)
            db.commit()
    finally:
        db.close()


def delete_test_department(department_id) -> None:
    db = SessionLocal()

    try:
        department = db.get(Department, department_id)

        if department is not None:
            db.delete(department)
            db.commit()
    finally:
        db.close()


def test_get_authority_returns_existing_authority():
    department = create_test_department()

    authority = create_test_authority(
        department_id=department.id,
        name="Existing Authority",
    )

    try:
        db = SessionLocal()

        try:
            result = get_authority(
                db=db,
                authority_id=authority.id,
            )

            assert result is not None
            assert result.id == authority.id
            assert result.name == "Existing Authority"
            assert result.department_id == department.id
        finally:
            db.close()
    finally:
        delete_test_authority(authority.id)
        delete_test_department(department.id)


def test_get_authority_returns_none_for_unknown_authority():
    db = SessionLocal()

    try:
        result = get_authority(
            db=db,
            authority_id=uuid4(),
        )

        assert result is None
    finally:
        db.close()


def test_list_authorities_returns_matching_search_results():
    department = create_test_department()

    first_authority = create_test_authority(
        department_id=department.id,
        name="Aakar Searchable Authority",
    )

    second_authority = create_test_authority(
        department_id=department.id,
        name="Completely Different Authority",
    )

    try:
        db = SessionLocal()

        try:
            authorities, total = list_authorities(
                db=db,
                search="searchable authority",
            )

            authority_ids = {item.id for item in authorities}

            assert total >= 1
            assert first_authority.id in authority_ids
            assert second_authority.id not in authority_ids
        finally:
            db.close()
    finally:
        delete_test_authority(first_authority.id)
        delete_test_authority(second_authority.id)
        delete_test_department(department.id)


def test_list_authorities_filters_by_department():
    first_department = create_test_department(
        name="First Department",
    )

    second_department = create_test_department(
        name="Second Department",
    )

    first_authority = create_test_authority(
        department_id=first_department.id,
        name="First Department Authority",
    )

    second_authority = create_test_authority(
        department_id=second_department.id,
        name="Second Department Authority",
    )

    try:
        db = SessionLocal()

        try:
            authorities, _ = list_authorities(
                db=db,
                department_id=first_department.id,
            )

            authority_ids = {item.id for item in authorities}

            assert first_authority.id in authority_ids
            assert second_authority.id not in authority_ids
        finally:
            db.close()
    finally:
        delete_test_authority(first_authority.id)
        delete_test_authority(second_authority.id)
        delete_test_department(first_department.id)
        delete_test_department(second_department.id)


def test_list_authorities_filters_by_authority_type():
    department = create_test_department()

    central_authority = create_test_authority(
        department_id=department.id,
        name="Central Authority",
        authority_type="CENTRAL",
    )

    state_authority = create_test_authority(
        department_id=department.id,
        name="State Authority",
        authority_type="STATE",
    )

    try:
        db = SessionLocal()

        try:
            authorities, _ = list_authorities(
                db=db,
                authority_type="state",
            )

            authority_ids = {item.id for item in authorities}

            assert state_authority.id in authority_ids
            assert central_authority.id not in authority_ids
        finally:
            db.close()
    finally:
        delete_test_authority(central_authority.id)
        delete_test_authority(state_authority.id)
        delete_test_department(department.id)


def test_list_authorities_filters_by_active_status():
    department = create_test_department()

    active_authority = create_test_authority(
        department_id=department.id,
        name="Active Authority",
    )

    inactive_authority = create_test_authority(
        department_id=department.id,
        name="Inactive Authority",
    )

    db = SessionLocal()

    try:
        set_authority_active_status(
            db=db,
            authority_id=inactive_authority.id,
            is_active=False,
        )
    finally:
        db.close()

    try:
        db = SessionLocal()

        try:
            authorities, _ = list_authorities(
                db=db,
                is_active=False,
            )

            authority_ids = {item.id for item in authorities}

            assert inactive_authority.id in authority_ids
            assert active_authority.id not in authority_ids
        finally:
            db.close()
    finally:
        delete_test_authority(active_authority.id)
        delete_test_authority(inactive_authority.id)
        delete_test_department(department.id)


def test_list_authorities_supports_pagination():
    department = create_test_department()

    first_authority = create_test_authority(
        department_id=department.id,
        name="Pagination Authority One",
    )

    second_authority = create_test_authority(
        department_id=department.id,
        name="Pagination Authority Two",
    )

    try:
        db = SessionLocal()

        try:
            authorities, total = list_authorities(
                db=db,
                search=TEST_PREFIX,
                offset=0,
                limit=1,
            )

            assert total >= 2
            assert len(authorities) == 1
        finally:
            db.close()
    finally:
        delete_test_authority(first_authority.id)
        delete_test_authority(second_authority.id)
        delete_test_department(department.id)


def test_create_authority_normalizes_values():
    department = create_test_department()
    authority_id = None

    db = SessionLocal()

    try:
        authority = create_authority(
            db=db,
            department_id=department.id,
            code="  test-authority  ",
            name="  Test Authority  ",
            authority_type="  state  ",
            description="  Authority description  ",
        )

        assert authority.code == "TEST-AUTHORITY"
        assert authority.name == "Test Authority"
        assert authority.authority_type == "STATE"
        assert authority.description == "Authority description"

        authority_id = authority.id
    finally:
        db.close()

    delete_test_authority(authority_id)
    delete_test_department(department.id)


def test_create_authority_rejects_duplicate_code():
    department = create_test_department()

    first_authority = create_test_authority(
        department_id=department.id,
        code=f"{TEST_PREFIX}-DUP",
        name="First Authority",
    )

    try:
        db = SessionLocal()

        try:
            with pytest.raises(ValueError, match="already exists"):
                create_authority(
                    db=db,
                    department_id=department.id,
                    code=f"{TEST_PREFIX}-dup",
                    name="Second Authority",
                    authority_type="STATE",
                )
        finally:
            db.close()
    finally:
        delete_test_authority(first_authority.id)
        delete_test_department(department.id)


def test_create_authority_rejects_invalid_type():
    department = create_test_department()

    try:
        db = SessionLocal()

        try:
            with pytest.raises(ValueError, match="Invalid authority type"):
                create_authority(
                    db=db,
                    department_id=department.id,
                    code=f"{TEST_PREFIX}-INVALID",
                    name="Invalid Authority",
                    authority_type="UNKNOWN",
                )
        finally:
            db.close()
    finally:
        delete_test_department(department.id)


def test_create_authority_rejects_unknown_department():
    db = SessionLocal()

    try:
        with pytest.raises(ValueError, match="Department not found"):
            create_authority(
                db=db,
                department_id=uuid4(),
                code=f"{TEST_PREFIX}-UNKNOWN",
                name="Unknown Department Authority",
                authority_type="STATE",
            )
    finally:
        db.close()


def test_create_authority_rejects_inactive_department():
    department = create_test_department(
        is_active=False,
    )

    try:
        db = SessionLocal()

        try:
            with pytest.raises(
                ValueError,
                match="inactive department",
            ):
                create_authority(
                    db=db,
                    department_id=department.id,
                    code=f"{TEST_PREFIX}-INACTIVE",
                    name="Inactive Department Authority",
                    authority_type="STATE",
                )
        finally:
            db.close()
    finally:
        delete_test_department(department.id)


def test_create_authority_accepts_all_supported_types():
    department = create_test_department()
    authority_ids = []

    try:
        db = SessionLocal()

        try:
            for authority_type in VALID_AUTHORITY_TYPES:
                authority = create_authority(
                    db=db,
                    department_id=department.id,
                    code=f"{TEST_PREFIX}-{authority_type}",
                    name=f"{authority_type} Authority",
                    authority_type=authority_type,
                )

                authority_ids.append(authority.id)

            assert len(authority_ids) == len(VALID_AUTHORITY_TYPES)
        finally:
            db.close()
    finally:
        for authority_id in authority_ids:
            delete_test_authority(authority_id)

        delete_test_department(department.id)


def test_update_authority_normalizes_values():
    department = create_test_department()

    authority = create_test_authority(
        department_id=department.id,
        code=f"{TEST_PREFIX}-UPD",
        name="Old Authority",
    )

    try:
        db = SessionLocal()

        try:
            updated_authority = update_authority(
                db=db,
                authority_id=authority.id,
                department_id=department.id,
                code="  updated-authority  ",
                name="  Updated Authority  ",
                authority_type="  district  ",
                description="  Updated description  ",
            )

            assert updated_authority.code == "UPDATED-AUTHORITY"
            assert updated_authority.name == "Updated Authority"
            assert updated_authority.authority_type == "DISTRICT"
            assert updated_authority.description == "Updated description"
        finally:
            db.close()
    finally:
        delete_test_authority(authority.id)
        delete_test_department(department.id)


def test_update_authority_can_move_between_departments():
    first_department = create_test_department(
        name="First Department",
    )

    second_department = create_test_department(
        name="Second Department",
    )

    authority = create_test_authority(
        department_id=first_department.id,
        name="Movable Authority",
    )

    try:
        db = SessionLocal()

        try:
            updated_authority = update_authority(
                db=db,
                authority_id=authority.id,
                department_id=second_department.id,
                code=authority.code,
                name=authority.name,
                authority_type=authority.authority_type,
                description=authority.description,
            )

            assert updated_authority.department_id == second_department.id
        finally:
            db.close()
    finally:
        delete_test_authority(authority.id)
        delete_test_department(first_department.id)
        delete_test_department(second_department.id)


def test_update_authority_rejects_duplicate_code():
    department = create_test_department()

    first_authority = create_test_authority(
        department_id=department.id,
        code=f"{TEST_PREFIX}-FIRST",
        name="First Authority",
    )

    second_authority = create_test_authority(
        department_id=department.id,
        code=f"{TEST_PREFIX}-SECOND",
        name="Second Authority",
    )

    try:
        db = SessionLocal()

        try:
            with pytest.raises(ValueError, match="already exists"):
                update_authority(
                    db=db,
                    authority_id=second_authority.id,
                    department_id=department.id,
                    code=first_authority.code,
                    name="Updated Second Authority",
                    authority_type="STATE",
                )
        finally:
            db.close()
    finally:
        delete_test_authority(first_authority.id)
        delete_test_authority(second_authority.id)
        delete_test_department(department.id)


def test_update_authority_rejects_invalid_type():
    department = create_test_department()

    authority = create_test_authority(
        department_id=department.id,
    )

    try:
        db = SessionLocal()

        try:
            with pytest.raises(ValueError, match="Invalid authority type"):
                update_authority(
                    db=db,
                    authority_id=authority.id,
                    department_id=department.id,
                    code=authority.code,
                    name=authority.name,
                    authority_type="UNKNOWN",
                )
        finally:
            db.close()
    finally:
        delete_test_authority(authority.id)
        delete_test_department(department.id)


def test_update_authority_rejects_inactive_department():
    first_department = create_test_department()
    second_department = create_test_department(
        is_active=False,
    )

    authority = create_test_authority(
        department_id=first_department.id,
    )

    try:
        db = SessionLocal()

        try:
            with pytest.raises(
                ValueError,
                match="inactive department",
            ):
                update_authority(
                    db=db,
                    authority_id=authority.id,
                    department_id=second_department.id,
                    code=authority.code,
                    name=authority.name,
                    authority_type=authority.authority_type,
                )
        finally:
            db.close()
    finally:
        delete_test_authority(authority.id)
        delete_test_department(first_department.id)
        delete_test_department(second_department.id)


def test_update_authority_rejects_unknown_authority():
    department = create_test_department()

    try:
        db = SessionLocal()

        try:
            with pytest.raises(ValueError, match="Authority not found"):
                update_authority(
                    db=db,
                    authority_id=uuid4(),
                    department_id=department.id,
                    code=f"{TEST_PREFIX}-UNKNOWN",
                    name="Unknown Authority",
                    authority_type="STATE",
                )
        finally:
            db.close()
    finally:
        delete_test_department(department.id)


def test_set_authority_active_status_changes_state():
    department = create_test_department()

    authority = create_test_authority(
        department_id=department.id,
        name="Status Authority",
    )

    try:
        db = SessionLocal()

        try:
            updated_authority = set_authority_active_status(
                db=db,
                authority_id=authority.id,
                is_active=False,
            )

            assert updated_authority.is_active is False

            updated_authority = set_authority_active_status(
                db=db,
                authority_id=authority.id,
                is_active=True,
            )

            assert updated_authority.is_active is True
        finally:
            db.close()
    finally:
        delete_test_authority(authority.id)
        delete_test_department(department.id)


def test_set_authority_active_status_unknown_authority_raises_error():
    db = SessionLocal()

    try:
        with pytest.raises(ValueError, match="Authority not found"):
            set_authority_active_status(
                db=db,
                authority_id=uuid4(),
                is_active=False,
            )
    finally:
        db.close()

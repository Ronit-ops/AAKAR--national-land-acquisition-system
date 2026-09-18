from uuid import uuid4

import pytest

from app.db.session import SessionLocal
from app.models.department import Department
from app.services.department_service import (
    create_department,
    get_department,
    list_departments,
    set_department_active_status,
    update_department,
)


TEST_PREFIX = "DPT-TEST"
TEST_PASSWORD = "AAKAR-Department-123!"


def create_test_department(
    *,
    code: str | None = None,
    name: str = "Test Department",
) -> Department:
    db = SessionLocal()

    try:
        return create_department(
            db=db,
            code=code or f"{TEST_PREFIX}-{uuid4().hex[:8].upper()}",
            name=name,
            description="Test department",
        )
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


def test_get_department_returns_existing_department():
    department = create_test_department(
        name="Existing Department",
    )

    try:
        db = SessionLocal()

        try:
            result = get_department(
                db=db,
                department_id=department.id,
            )

            assert result is not None
            assert result.id == department.id
            assert result.name == "Existing Department"
        finally:
            db.close()
    finally:
        delete_test_department(department.id)


def test_get_department_returns_none_for_unknown_department():
    db = SessionLocal()

    try:
        result = get_department(
            db=db,
            department_id=uuid4(),
        )

        assert result is None
    finally:
        db.close()


def test_list_departments_returns_matching_search_results():
    first_department = create_test_department(
        name="Aakar Searchable Department",
    )

    second_department = create_test_department(
        name="Completely Different Department",
    )

    try:
        db = SessionLocal()

        try:
            departments, total = list_departments(
                db=db,
                search="searchable department",
            )

            department_ids = {item.id for item in departments}

            assert total >= 1
            assert first_department.id in department_ids
            assert second_department.id not in department_ids
        finally:
            db.close()
    finally:
        delete_test_department(first_department.id)
        delete_test_department(second_department.id)


def test_list_departments_filters_by_active_status():
    active_department = create_test_department(
        name="Active Department",
    )

    inactive_department = create_test_department(
        name="Inactive Department",
    )

    db = SessionLocal()

    try:
        set_department_active_status(
            db=db,
            department_id=inactive_department.id,
            is_active=False,
        )
    finally:
        db.close()

    try:
        db = SessionLocal()

        try:
            departments, _ = list_departments(
                db=db,
                is_active=False,
            )

            department_ids = {item.id for item in departments}

            assert inactive_department.id in department_ids
            assert active_department.id not in department_ids
        finally:
            db.close()
    finally:
        delete_test_department(active_department.id)
        delete_test_department(inactive_department.id)


def test_list_departments_supports_pagination():
    first_department = create_test_department(
        name="Pagination One",
    )

    second_department = create_test_department(
        name="Pagination Two",
    )

    try:
        db = SessionLocal()

        try:
            departments, total = list_departments(
                db=db,
                search=TEST_PREFIX,
                offset=0,
                limit=1,
            )

            assert total >= 2
            assert len(departments) == 1
        finally:
            db.close()
    finally:
        delete_test_department(first_department.id)
        delete_test_department(second_department.id)


def test_create_department_normalizes_values():
    department_id = None

    db = SessionLocal()

    try:
        department = create_department(
            db=db,
            code="  test-dept  ",
            name="  Test Department  ",
            description="  Department description  ",
        )

        assert department.code == "TEST-DEPT"
        assert department.name == "Test Department"
        assert department.description == "Department description"

        department_id = department.id
    finally:
        db.close()

    delete_test_department(department_id)


def test_create_department_rejects_duplicate_code():
    first_department = create_test_department(
        code=f"{TEST_PREFIX}-DUP",
        name="First Department",
    )

    try:
        db = SessionLocal()

        try:
            with pytest.raises(ValueError, match="already exists"):
                create_department(
                    db=db,
                    code=f"{TEST_PREFIX}-dup",
                    name="Second Department",
                )
        finally:
            db.close()
    finally:
        delete_test_department(first_department.id)


def test_create_department_rejects_empty_values():
    db = SessionLocal()

    try:
        with pytest.raises(ValueError, match="code must not be empty"):
            create_department(
                db=db,
                code="   ",
                name="Valid Name",
            )

        with pytest.raises(ValueError, match="name must not be empty"):
            create_department(
                db=db,
                code="VALID-CODE",
                name="   ",
            )
    finally:
        db.rollback()
        db.close()


def test_update_department_normalizes_values():
    department = create_test_department(
        code=f"{TEST_PREFIX}-UPD",
        name="Old Department",
    )

    try:
        db = SessionLocal()

        try:
            updated_department = update_department(
                db=db,
                department_id=department.id,
                code="  updated-dept  ",
                name="  Updated Department  ",
                description="  Updated description  ",
            )

            assert updated_department.code == "UPDATED-DEPT"
            assert updated_department.name == "Updated Department"
            assert updated_department.description == "Updated description"
        finally:
            db.close()
    finally:
        delete_test_department(department.id)


def test_update_department_rejects_duplicate_code():
    first_department = create_test_department(
        code=f"{TEST_PREFIX}-FIRST",
        name="First Department",
    )

    second_department = create_test_department(
        code=f"{TEST_PREFIX}-SECOND",
        name="Second Department",
    )

    try:
        db = SessionLocal()

        try:
            with pytest.raises(ValueError, match="already exists"):
                update_department(
                    db=db,
                    department_id=second_department.id,
                    code=first_department.code,
                    name="Updated Second Department",
                )
        finally:
            db.close()
    finally:
        delete_test_department(first_department.id)
        delete_test_department(second_department.id)


def test_update_unknown_department_raises_error():
    db = SessionLocal()

    try:
        with pytest.raises(ValueError, match="Department not found"):
            update_department(
                db=db,
                department_id=uuid4(),
                code="UNKNOWN-DEPARTMENT",
                name="Unknown Department",
            )
    finally:
        db.close()


def test_set_department_active_status_changes_state():
    department = create_test_department(
        name="Status Department",
    )

    try:
        db = SessionLocal()

        try:
            updated_department = set_department_active_status(
                db=db,
                department_id=department.id,
                is_active=False,
            )

            assert updated_department.is_active is False

            updated_department = set_department_active_status(
                db=db,
                department_id=department.id,
                is_active=True,
            )

            assert updated_department.is_active is True
        finally:
            db.close()
    finally:
        delete_test_department(department.id)


def test_set_department_active_status_unknown_department_raises_error():
    db = SessionLocal()

    try:
        with pytest.raises(ValueError, match="Department not found"):
            set_department_active_status(
                db=db,
                department_id=uuid4(),
                is_active=False,
            )
    finally:
        db.close()

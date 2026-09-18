from uuid import uuid4

import pytest

from app.db.session import SessionLocal
from app.models.authority import Authority
from app.models.department import Department
from app.models.user import User
from app.services.authority_service import create_authority
from app.services.department_service import create_department
from app.services.auth_service import create_user
from app.services.user_management_service import set_user_organization


TEST_PASSWORD = "AAKAR-Organization-123!"


def create_test_department(
    *,
    name: str = "Test Department",
    is_active: bool = True,
) -> Department:
    db = SessionLocal()

    try:
        department = create_department(
            db=db,
            code=f"DPT-{uuid4().hex[:8].upper()}",
            name=name,
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
    name: str = "Test Authority",
    is_active: bool = True,
) -> Authority:
    db = SessionLocal()

    try:
        authority = create_authority(
            db=db,
            department_id=department_id,
            code=f"AUTH-{uuid4().hex[:8].upper()}",
            name=name,
            authority_type="STATE",
        )

        if not is_active:
            authority.is_active = False
            db.commit()
            db.refresh(authority)

        return authority
    finally:
        db.close()


def create_test_user() -> User:
    db = SessionLocal()

    try:
        return create_user(
            db=db,
            email=f"organization-user-{uuid4()}@example.com",
            password=TEST_PASSWORD,
            full_name="Organization Test User",
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


def test_assigns_user_to_department_and_authority():
    user = create_test_user()
    department = create_test_department()
    authority = create_test_authority(
        department_id=department.id,
    )

    try:
        db = SessionLocal()

        try:
            updated_user = set_user_organization(
                db=db,
                user_id=user.id,
                department_id=department.id,
                authority_id=authority.id,
            )

            assert updated_user.department_id == department.id
            assert updated_user.authority_id == authority.id
        finally:
            db.close()
    finally:
        delete_test_user(user.id)
        delete_test_authority(authority.id)
        delete_test_department(department.id)


def test_assigns_user_to_department_without_authority():
    user = create_test_user()
    department = create_test_department()

    try:
        db = SessionLocal()

        try:
            updated_user = set_user_organization(
                db=db,
                user_id=user.id,
                department_id=department.id,
                authority_id=None,
            )

            assert updated_user.department_id == department.id
            assert updated_user.authority_id is None
        finally:
            db.close()
    finally:
        delete_test_user(user.id)
        delete_test_department(department.id)


def test_clears_user_organization():
    user = create_test_user()
    department = create_test_department()
    authority = create_test_authority(
        department_id=department.id,
    )

    try:
        db = SessionLocal()

        try:
            set_user_organization(
                db=db,
                user_id=user.id,
                department_id=department.id,
                authority_id=authority.id,
            )

            updated_user = set_user_organization(
                db=db,
                user_id=user.id,
                department_id=None,
                authority_id=None,
            )

            assert updated_user.department_id is None
            assert updated_user.authority_id is None
        finally:
            db.close()
    finally:
        delete_test_user(user.id)
        delete_test_authority(authority.id)
        delete_test_department(department.id)


def test_rejects_authority_without_department():
    user = create_test_user()
    authority_department = create_test_department()
    authority = create_test_authority(
        department_id=authority_department.id,
    )

    try:
        db = SessionLocal()

        try:
            with pytest.raises(
                ValueError,
                match="requires a department",
            ):
                set_user_organization(
                    db=db,
                    user_id=user.id,
                    department_id=None,
                    authority_id=authority.id,
                )
        finally:
            db.close()
    finally:
        delete_test_user(user.id)
        delete_test_authority(authority.id)
        delete_test_department(authority_department.id)


def test_rejects_unknown_department():
    user = create_test_user()

    try:
        db = SessionLocal()

        try:
            with pytest.raises(
                ValueError,
                match="Department not found",
            ):
                set_user_organization(
                    db=db,
                    user_id=user.id,
                    department_id=uuid4(),
                    authority_id=None,
                )
        finally:
            db.close()
    finally:
        delete_test_user(user.id)


def test_rejects_unknown_authority():
    user = create_test_user()
    department = create_test_department()

    try:
        db = SessionLocal()

        try:
            with pytest.raises(
                ValueError,
                match="Authority not found",
            ):
                set_user_organization(
                    db=db,
                    user_id=user.id,
                    department_id=department.id,
                    authority_id=uuid4(),
                )
        finally:
            db.close()
    finally:
        delete_test_user(user.id)
        delete_test_department(department.id)


def test_rejects_inactive_department():
    user = create_test_user()
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
                set_user_organization(
                    db=db,
                    user_id=user.id,
                    department_id=department.id,
                    authority_id=None,
                )
        finally:
            db.close()
    finally:
        delete_test_user(user.id)
        delete_test_department(department.id)


def test_rejects_inactive_authority():
    user = create_test_user()
    department = create_test_department()
    authority = create_test_authority(
        department_id=department.id,
        is_active=False,
    )

    try:
        db = SessionLocal()

        try:
            with pytest.raises(
                ValueError,
                match="inactive authority",
            ):
                set_user_organization(
                    db=db,
                    user_id=user.id,
                    department_id=department.id,
                    authority_id=authority.id,
                )
        finally:
            db.close()
    finally:
        delete_test_user(user.id)
        delete_test_authority(authority.id)
        delete_test_department(department.id)


def test_rejects_authority_from_different_department():
    user = create_test_user()
    first_department = create_test_department(
        name="First Department",
    )
    second_department = create_test_department(
        name="Second Department",
    )
    authority = create_test_authority(
        department_id=second_department.id,
    )

    try:
        db = SessionLocal()

        try:
            with pytest.raises(
                ValueError,
                match="does not belong",
            ):
                set_user_organization(
                    db=db,
                    user_id=user.id,
                    department_id=first_department.id,
                    authority_id=authority.id,
                )
        finally:
            db.close()
    finally:
        delete_test_user(user.id)
        delete_test_authority(authority.id)
        delete_test_department(first_department.id)
        delete_test_department(second_department.id)


def test_rejects_unknown_user():
    department = create_test_department()

    try:
        db = SessionLocal()

        try:
            with pytest.raises(
                ValueError,
                match="User not found",
            ):
                set_user_organization(
                    db=db,
                    user_id=uuid4(),
                    department_id=department.id,
                    authority_id=None,
                )
        finally:
            db.close()
    finally:
        delete_test_department(department.id)

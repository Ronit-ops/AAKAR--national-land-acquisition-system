from uuid import uuid4

import pytest
from sqlalchemy import delete

from app.db.session import SessionLocal
from app.models.permission import Permission
from app.services.permission_service import (
    create_permission,
    get_permission,
    list_permissions,
    set_permission_active_status,
    update_permission,
)


TEST_CODE_PREFIX = "test.permission.service"


def cleanup_test_permissions():
    db = SessionLocal()

    try:
        db.execute(
            delete(Permission).where(
                Permission.code.like(f"{TEST_CODE_PREFIX}.%")
            )
        )
        db.commit()
    finally:
        db.close()


@pytest.fixture(autouse=True)
def cleanup_permissions():
    cleanup_test_permissions()
    yield
    cleanup_test_permissions()


def test_create_permission_normalizes_values():
    db = SessionLocal()

    try:
        permission = create_permission(
            db=db,
            code="  TEST.PERMISSION.SERVICE.CREATE  ",
            name="  Test Permission  ",
            resource="  TEST  ",
            action="  CREATE  ",
            description="  Test description  ",
            is_system_permission=False,
        )

        assert permission.code == "test.permission.service.create"
        assert permission.name == "Test Permission"
        assert permission.resource == "test"
        assert permission.action == "create"
        assert permission.description == "Test description"
        assert permission.is_system_permission is False
        assert permission.is_active is True

    finally:
        db.close()


def test_create_permission_rejects_duplicate_code():
    db = SessionLocal()

    try:
        create_permission(
            db=db,
            code="test.permission.service.duplicate",
            name="Duplicate Permission",
            resource="test",
            action="duplicate",
            is_system_permission=False,
        )

        with pytest.raises(
            ValueError,
            match="A permission with this code already exists.",
        ):
            create_permission(
                db=db,
                code="TEST.PERMISSION.SERVICE.DUPLICATE",
                name="Another Permission",
                resource="test",
                action="duplicate",
                is_system_permission=False,
            )

    finally:
        db.close()


@pytest.mark.parametrize(
    "code,name,resource,action,expected_message",
    [
        (
            "   ",
            "Test Permission",
            "test",
            "read",
            "Permission code must not be empty.",
        ),
        (
            "test.permission.service.empty-name",
            "   ",
            "test",
            "read",
            "Permission name must not be empty.",
        ),
        (
            "test.permission.service.empty-resource",
            "Test Permission",
            "   ",
            "read",
            "Permission resource must not be empty.",
        ),
        (
            "test.permission.service.empty-action",
            "Test Permission",
            "test",
            "   ",
            "Permission action must not be empty.",
        ),
    ],
)
def test_create_permission_rejects_empty_values(
    code,
    name,
    resource,
    action,
    expected_message,
):
    db = SessionLocal()

    try:
        with pytest.raises(ValueError, match=expected_message):
            create_permission(
                db=db,
                code=code,
                name=name,
                resource=resource,
                action=action,
                is_system_permission=False,
            )

    finally:
        db.close()


def test_get_permission():
    db = SessionLocal()

    try:
        created = create_permission(
            db=db,
            code="test.permission.service.get",
            name="Get Permission",
            resource="test",
            action="get",
            is_system_permission=False,
        )

        found = get_permission(
            db=db,
            permission_id=created.id,
        )

        assert found is not None
        assert found.id == created.id
        assert found.code == "test.permission.service.get"

        missing = get_permission(
            db=db,
            permission_id=uuid4(),
        )

        assert missing is None

    finally:
        db.close()


def test_list_permissions_search_and_filters():
    db = SessionLocal()

    try:
        create_permission(
            db=db,
            code="test.permission.service.alpha",
            name="Alpha Permission",
            resource="test",
            action="read",
            is_system_permission=False,
        )

        create_permission(
            db=db,
            code="test.permission.service.beta",
            name="Beta Permission",
            resource="test",
            action="write",
            is_system_permission=False,
        )

        create_permission(
            db=db,
            code="test.permission.service.gamma",
            name="Gamma Permission",
            resource="other",
            action="read",
            is_system_permission=False,
        )

        permissions, total = list_permissions(
            db=db,
            search="test.permission.service.alpha",
            offset=0,
            limit=20,
        )

        assert total == 1
        assert len(permissions) == 1
        assert permissions[0].code == "test.permission.service.alpha"

        permissions, total = list_permissions(
            db=db,
            search="test.permission.service.beta",
            offset=0,
            limit=20,
        )

        assert total == 1
        assert len(permissions) == 1
        assert permissions[0].code == "test.permission.service.beta"

        permissions, total = list_permissions(
            db=db,
            search="test.permission.service.gamma",
            offset=0,
            limit=20,
        )

        assert total == 1
        assert len(permissions) == 1
        assert permissions[0].code == "test.permission.service.gamma"

    finally:
        db.close()


def test_list_permissions_active_filter_and_pagination():
    db = SessionLocal()

    try:
        first = create_permission(
            db=db,
            code="test.permission.service.page-one",
            name="Page One",
            resource="test",
            action="page",
            is_system_permission=False,
        )

        second = create_permission(
            db=db,
            code="test.permission.service.page-two",
            name="Page Two",
            resource="test",
            action="page",
            is_system_permission=False,
        )

        set_permission_active_status(
            db=db,
            permission_id=second.id,
            is_active=False,
        )

        permissions, total = list_permissions(
            db=db,
            search="test.permission.service.page",
            is_active=True,
            offset=0,
            limit=1,
        )

        assert total == 1
        assert len(permissions) == 1
        assert permissions[0].id == first.id

        permissions, total = list_permissions(
            db=db,
            search="test.permission.service.page",
            is_active=False,
            offset=0,
            limit=20,
        )

        assert total == 1
        assert len(permissions) == 1
        assert permissions[0].id == second.id

    finally:
        db.close()


def test_list_permissions_pagination():
    db = SessionLocal()

    try:
        create_permission(
            db=db,
            code="test.permission.service.first-page",
            name="First Page",
            resource="test",
            action="page",
            is_system_permission=False,
        )

        create_permission(
            db=db,
            code="test.permission.service.second-page",
            name="Second Page",
            resource="test",
            action="page",
            is_system_permission=False,
        )

        create_permission(
            db=db,
            code="test.permission.service.third-page",
            name="Third Page",
            resource="test",
            action="page",
            is_system_permission=False,
        )

        permissions, total = list_permissions(
            db=db,
            search="test.permission.service.",
            offset=1,
            limit=1,
        )

        assert total == 3
        assert len(permissions) == 1
        assert (
            permissions[0].code
            == "test.permission.service.second-page"
        )

    finally:
        db.close()


def test_update_permission():
    db = SessionLocal()

    try:
        permission = create_permission(
            db=db,
            code="test.permission.service.update",
            name="Original Name",
            resource="test",
            action="read",
            description="Original description",
            is_system_permission=False,
        )

        updated = update_permission(
            db=db,
            permission_id=permission.id,
            code=" TEST.PERMISSION.SERVICE.UPDATED ",
            name=" Updated Name ",
            resource=" TEST ",
            action=" WRITE ",
            description=" Updated description ",
        )

        assert updated.id == permission.id
        assert updated.code == "test.permission.service.updated"
        assert updated.name == "Updated Name"
        assert updated.resource == "test"
        assert updated.action == "write"
        assert updated.description == "Updated description"

    finally:
        db.close()


def test_update_permission_rejects_duplicate_code():
    db = SessionLocal()

    try:
        first = create_permission(
            db=db,
            code="test.permission.service.first",
            name="First Permission",
            resource="test",
            action="first",
            is_system_permission=False,
        )

        second = create_permission(
            db=db,
            code="test.permission.service.second",
            name="Second Permission",
            resource="test",
            action="second",
            is_system_permission=False,
        )

        with pytest.raises(
            ValueError,
            match="A permission with this code already exists.",
        ):
            update_permission(
                db=db,
                permission_id=second.id,
                code=first.code,
                name="Updated Second Permission",
                resource="test",
                action="updated",
            )

    finally:
        db.close()


def test_update_permission_not_found():
    db = SessionLocal()

    try:
        with pytest.raises(
            ValueError,
            match="Permission not found.",
        ):
            update_permission(
                db=db,
                permission_id=uuid4(),
                code="test.permission.service.not-found",
                name="Not Found Permission",
                resource="test",
                action="read",
            )

    finally:
        db.close()


def test_set_permission_active_status():
    db = SessionLocal()

    try:
        permission = create_permission(
            db=db,
            code="test.permission.service.status",
            name="Status Permission",
            resource="test",
            action="status",
            is_system_permission=False,
        )

        assert permission.is_active is True

        updated = set_permission_active_status(
            db=db,
            permission_id=permission.id,
            is_active=False,
        )

        assert updated.is_active is False

        updated = set_permission_active_status(
            db=db,
            permission_id=permission.id,
            is_active=True,
        )

        assert updated.is_active is True

    finally:
        db.close()


def test_set_permission_active_status_not_found():
    db = SessionLocal()

    try:
        with pytest.raises(
            ValueError,
            match="Permission not found.",
        ):
            set_permission_active_status(
                db=db,
                permission_id=uuid4(),
                is_active=False,
            )

    finally:
        db.close()
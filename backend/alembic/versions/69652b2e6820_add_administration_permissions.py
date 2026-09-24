"""add administration permissions

Revision ID: 69652b2e6820
Revises: 95ec17fcf782
Create Date: 2026-09-24
"""

from typing import Sequence, Union
from uuid import uuid4

from alembic import op
import sqlalchemy as sa


revision: str = "69652b2e6820"
down_revision: Union[str, Sequence[str], None] = "95ec17fcf782"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ROLE_CODE = "system_administrator"

PERMISSIONS = [
    {
        "code": "user.read",
        "name": "View Users",
        "resource": "user",
        "action": "read",
        "description": "View managed AAKAR user accounts.",
    },
    {
        "code": "department.read",
        "name": "View Departments",
        "resource": "department",
        "action": "read",
        "description": "View AAKAR departments.",
    },
    {
        "code": "authority.read",
        "name": "View Authorities",
        "resource": "authority",
        "action": "read",
        "description": "View AAKAR authorities.",
    },
    {
        "code": "permission.read",
        "name": "View Permissions",
        "resource": "permission",
        "action": "read",
        "description": "View configured AAKAR permissions.",
    },
]


def upgrade() -> None:
    """Create administration read permissions and assign them to system administrators."""

    connection = op.get_bind()

    # Find the existing system administrator role.
    role_id = connection.execute(
        sa.text(
            """
            SELECT id
            FROM roles
            WHERE code = :role_code
            """
        ),
        {
            "role_code": ROLE_CODE,
        },
    ).scalar_one_or_none()

    if role_id is None:
        raise RuntimeError(
            "Role 'system_administrator' was not found."
        )

    for permission in PERMISSIONS:

        # Check whether the permission already exists.
        permission_id = connection.execute(
            sa.text(
                """
                SELECT id
                FROM permissions
                WHERE code = :code
                """
            ),
            {
                "code": permission["code"],
            },
        ).scalar_one_or_none()

        # Create the permission if it does not exist.
        if permission_id is None:
            permission_id = connection.execute(
                sa.text(
                    """
                    INSERT INTO permissions (
                        id,
                        code,
                        name,
                        resource,
                        action,
                        description
                    )
                    VALUES (
                        :id,
                        :code,
                        :name,
                        :resource,
                        :action,
                        :description
                    )
                    RETURNING id
                    """
                ),
                {
                    "id": uuid4(),
                    **permission,
                },
            ).scalar_one()

        # Make sure the role has this permission.
        connection.execute(
            sa.text(
                """
                INSERT INTO role_permissions (
                    role_id,
                    permission_id
                )
                VALUES (
                    :role_id,
                    :permission_id
                )
                ON CONFLICT (role_id, permission_id)
                DO NOTHING
                """
            ),
            {
                "role_id": role_id,
                "permission_id": permission_id,
            },
        )


def downgrade() -> None:
    """Remove administration read permissions created by this migration."""

    connection = op.get_bind()

    permission_codes = [
        permission["code"]
        for permission in PERMISSIONS
    ]

    # Remove role assignments first because of the foreign key.
    connection.execute(
        sa.text(
            """
            DELETE FROM role_permissions
            WHERE role_id = (
                SELECT id
                FROM roles
                WHERE code = :role_code
            )
            AND permission_id IN (
                SELECT id
                FROM permissions
                WHERE code = ANY(:permission_codes)
            )
            """
        ),
        {
            "role_code": ROLE_CODE,
            "permission_codes": permission_codes,
        },
    )

    # Remove the permissions themselves.
    connection.execute(
        sa.text(
            """
            DELETE FROM permissions
            WHERE code = ANY(:permission_codes)
            """
        ),
        {
            "permission_codes": permission_codes,
        },
    )
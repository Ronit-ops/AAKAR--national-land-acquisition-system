"""add audit read permission

Revision ID: 0dc0831e7e03
Revises: 0f27f010455b
Create Date: 2026-09-21
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0dc0831e7e03"
down_revision: str | None = "0f27f010455b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


PERMISSION_CODE = "audit.read"

ROLE_CODES = (
    "national_administrator",
    "national_monitoring_officer",
    "audit_compliance",
)


def upgrade() -> None:
    connection = op.get_bind()

    permission_id = connection.execute(
        sa.text(
            """
            SELECT id
            FROM permissions
            WHERE code = :code
            """
        ),
        {"code": PERMISSION_CODE},
    ).scalar_one_or_none()

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
                    description,
                    is_system_permission,
                    is_active
                )
                VALUES (
                    gen_random_uuid(),
                    :code,
                    :name,
                    :resource,
                    :action,
                    :description,
                    :is_system_permission,
                    :is_active
                )
                RETURNING id
                """
            ),
            {
                "code": PERMISSION_CODE,
                "name": "View Audit History",
                "resource": "audit",
                "action": "read",
                "description": (
                    "View audit and activity history records, including "
                    "actor, action, entity, result, and event context."
                ),
                "is_system_permission": True,
                "is_active": True,
            },
        ).scalar_one()
    else:
        connection.execute(
            sa.text(
                """
                UPDATE permissions
                SET
                    name = :name,
                    resource = :resource,
                    action = :action,
                    description = :description,
                    is_system_permission = :is_system_permission,
                    is_active = :is_active,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :permission_id
                """
            ),
            {
                "permission_id": permission_id,
                "name": "View Audit History",
                "resource": "audit",
                "action": "read",
                "description": (
                    "View audit and activity history records, including "
                    "actor, action, entity, result, and event context."
                ),
                "is_system_permission": True,
                "is_active": True,
            },
        )

    roles = connection.execute(
        sa.text(
            """
            SELECT id, code
            FROM roles
            WHERE code = ANY(:role_codes)
        """
        ),
        {"role_codes": list(ROLE_CODES)},
    ).fetchall()

    found_role_codes = {row.code for row in roles}
    missing_role_codes = set(ROLE_CODES) - found_role_codes

    if missing_role_codes:
        raise RuntimeError(
            "Cannot assign audit.read because these roles do not exist: "
            + ", ".join(sorted(missing_role_codes))
        )

    for role in roles:
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
                ON CONFLICT (role_id, permission_id) DO NOTHING
                """
            ),
            {
                "role_id": role.id,
                "permission_id": permission_id,
            },
        )


def downgrade() -> None:
    connection = op.get_bind()

    permission_id = connection.execute(
        sa.text(
            """
            SELECT id
            FROM permissions
            WHERE code = :code
            """
        ),
        {"code": PERMISSION_CODE},
    ).scalar_one_or_none()

    if permission_id is None:
        return

    connection.execute(
        sa.text(
            """
            DELETE FROM role_permissions
            WHERE permission_id = :permission_id
            """
        ),
        {"permission_id": permission_id},
    )

    connection.execute(
        sa.text(
            """
            DELETE FROM permissions
            WHERE id = :permission_id
            """
        ),
        {"permission_id": permission_id},
    )
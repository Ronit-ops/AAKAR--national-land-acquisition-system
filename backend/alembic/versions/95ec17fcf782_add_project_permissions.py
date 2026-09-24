"""add project permissions

Revision ID: 95ec17fcf782
Revises: 4a50637fa652
Create Date: 2026-09-22
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "95ec17fcf782"
down_revision: Union[str, Sequence[str], None] = "4a50637fa652"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


PERMISSIONS = [
    {
        "code": "project.read",
        "name": "View Projects",
        "resource": "project",
        "action": "read",
        "description": (
            "View and search infrastructure project records "
            "within the user's authorized scope."
        ),
        "is_system_permission": True,
        "is_active": True,
    },
    {
        "code": "project.create",
        "name": "Create Projects",
        "resource": "project",
        "action": "create",
        "description": "Create infrastructure project records.",
        "is_system_permission": True,
        "is_active": True,
    },
    {
        "code": "project.update",
        "name": "Update Projects",
        "resource": "project",
        "action": "update",
        "description": "Update infrastructure project information.",
        "is_system_permission": True,
        "is_active": True,
    },
    {
        "code": "project.activate",
        "name": "Activate Projects",
        "resource": "project",
        "action": "activate",
        "description": "Activate a project from the draft lifecycle state.",
        "is_system_permission": True,
        "is_active": True,
    },
    {
        "code": "project.close",
        "name": "Close Projects",
        "resource": "project",
        "action": "close",
        "description": "Close an active project.",
        "is_system_permission": True,
        "is_active": True,
    },
]


ROLE_PERMISSION_CODES = {
    "project.read": (
        "national_administrator",
        "central_ministry_officer",
        "national_monitoring_officer",
        "state_nodal_officer",
        "state_land_authority_officer",
        "state_department_officer",
        "district_collector",
        "additional_collector",
        "land_acquisition_officer",
        "project_director",
        "infrastructure_officer",
        "field_verification_officer",
        "system_administrator",
        "audit_compliance",
    ),
    "project.create": (
        "national_administrator",
        "project_director",
        "system_administrator",
    ),
    "project.update": (
        "national_administrator",
        "project_director",
        "system_administrator",
    ),
    "project.activate": (
        "national_administrator",
        "project_director",
        "system_administrator",
    ),
    "project.close": (
        "national_administrator",
        "project_director",
        "system_administrator",
    ),
}


def upgrade() -> None:
    """Create project permissions and assign them to baseline roles."""
    connection = op.get_bind()

    permission_ids: dict[str, object] = {}

    for permission in PERMISSIONS:
        permission_id = connection.execute(
            sa.text(
                """
                SELECT id
                FROM permissions
                WHERE code = :code
                """
            ),
            {"code": permission["code"]},
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
                permission,
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
                    **permission,
                    "permission_id": permission_id,
                },
            )

        permission_ids[permission["code"]] = permission_id

    all_role_codes = sorted(
        {
            role_code
            for role_codes in ROLE_PERMISSION_CODES.values()
            for role_code in role_codes
        }
    )

    roles = connection.execute(
        sa.text(
            """
            SELECT id, code
            FROM roles
            WHERE code = ANY(:role_codes)
              AND is_active = TRUE
            """
        ),
        {"role_codes": all_role_codes},
    ).fetchall()

    found_role_codes = {row.code for row in roles}
    missing_role_codes = set(all_role_codes) - found_role_codes

    if missing_role_codes:
        raise RuntimeError(
            "Cannot assign project permissions because these active roles "
            "do not exist: "
            + ", ".join(sorted(missing_role_codes))
        )

    role_ids = {
        row.code: row.id
        for row in roles
    }

    for permission_code, role_codes in ROLE_PERMISSION_CODES.items():
        permission_id = permission_ids[permission_code]

        for role_code in role_codes:
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
                    "role_id": role_ids[role_code],
                    "permission_id": permission_id,
                },
            )


def downgrade() -> None:
    """Remove project permission assignments and definitions."""
    connection = op.get_bind()

    permission_codes = [
        permission["code"]
        for permission in PERMISSIONS
    ]

    permission_ids = connection.execute(
        sa.text(
            """
            SELECT id
            FROM permissions
            WHERE code = ANY(:permission_codes)
            """
        ),
        {"permission_codes": permission_codes},
    ).fetchall()

    for row in permission_ids:
        connection.execute(
            sa.text(
                """
                DELETE FROM role_permissions
                WHERE permission_id = :permission_id
                """
            ),
            {"permission_id": row.id},
        )

    connection.execute(
        sa.text(
            """
            DELETE FROM permissions
            WHERE code = ANY(:permission_codes)
            """
        ),
        {"permission_codes": permission_codes},
    )
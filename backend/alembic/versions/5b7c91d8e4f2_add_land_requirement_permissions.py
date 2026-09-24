"""add land requirement permissions

Revision ID: 5b7c91d8e4f2
Revises: 41ea153b2421
Create Date: 2026-09-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "5b7c91d8e4f2"
down_revision: Union[str, Sequence[str], None] = "41ea153b2421"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


PERMISSIONS = [
    {
        "code": "land_requirement.read",
        "name": "View Land Requirements",
        "resource": "land_requirement",
        "action": "read",
        "description": (
            "View and search land requirement records "
            "within the user's authorized scope."
        ),
        "is_system_permission": True,
        "is_active": True,
    },
    {
        "code": "land_requirement.create",
        "name": "Create Land Requirements",
        "resource": "land_requirement",
        "action": "create",
        "description": "Create land requirement records.",
        "is_system_permission": True,
        "is_active": True,
    },
    {
        "code": "land_requirement.update",
        "name": "Update Land Requirements",
        "resource": "land_requirement",
        "action": "update",
        "description": "Update editable land requirement information.",
        "is_system_permission": True,
        "is_active": True,
    },
    {
        "code": "land_requirement.submit",
        "name": "Submit Land Requirements",
        "resource": "land_requirement",
        "action": "submit",
        "description": "Submit land requirements for review.",
        "is_system_permission": True,
        "is_active": True,
    },
    {
        "code": "land_requirement.review",
        "name": "Review Land Requirements",
        "resource": "land_requirement",
        "action": "review",
        "description": (
            "Approve or reject land requirements under review."
        ),
        "is_system_permission": True,
        "is_active": True,
    },
    {
        "code": "land_requirement.withdraw",
        "name": "Withdraw Land Requirements",
        "resource": "land_requirement",
        "action": "withdraw",
        "description": "Withdraw an eligible land requirement.",
        "is_system_permission": True,
        "is_active": True,
    },
]


# Initial baseline assignments intentionally follow the existing
# Project permission pattern. Final AAKAR RBAC will be reconciled later.
ROLE_PERMISSION_CODES = {
    "land_requirement.read": (
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
    "land_requirement.create": (
        "national_administrator",
        "project_director",
        "system_administrator",
    ),
    "land_requirement.update": (
        "national_administrator",
        "project_director",
        "system_administrator",
    ),
    "land_requirement.submit": (
        "national_administrator",
        "project_director",
        "system_administrator",
    ),
    "land_requirement.review": (
        "national_administrator",
        "project_director",
        "system_administrator",
    ),
    "land_requirement.withdraw": (
        "national_administrator",
        "project_director",
        "system_administrator",
    ),
}


def upgrade() -> None:
    """Create land requirement permissions and assign them to baseline roles."""
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
            "Cannot assign land requirement permissions because these "
            "active roles do not exist: "
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
    """Remove land requirement permission assignments and definitions."""
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
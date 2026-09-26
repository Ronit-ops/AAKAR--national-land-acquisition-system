"""add acquisition case permissions

Revision ID: 7c1f4a9e6b21
Revises: 2e8f5fa53393
Create Date: 2026-09-26
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7c1f4a9e6b21"
down_revision: Union[str, Sequence[str], None] = "2e8f5fa53393"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


PERMISSIONS = [
    {
        "code": "acquisition_case.read",
        "name": "View Acquisition Cases",
        "resource": "acquisition_case",
        "action": "read",
        "description": (
            "View and search acquisition case records "
            "within the user's authorized scope."
        ),
        "is_system_permission": True,
        "is_active": True,
    },
    {
        "code": "acquisition_case.create",
        "name": "Create Acquisition Cases",
        "resource": "acquisition_case",
        "action": "create",
        "description": "Create acquisition case records.",
        "is_system_permission": True,
        "is_active": True,
    },
    {
        "code": "acquisition_case.update",
        "name": "Update Acquisition Cases",
        "resource": "acquisition_case",
        "action": "update",
        "description": "Update editable acquisition case information.",
        "is_system_permission": True,
        "is_active": True,
    },
    {
        "code": "acquisition_case.activate",
        "name": "Activate Acquisition Cases",
        "resource": "acquisition_case",
        "action": "activate",
        "description": "Activate an acquisition case from the draft state.",
        "is_system_permission": True,
        "is_active": True,
    },
    {
        "code": "acquisition_case.hold",
        "name": "Place Acquisition Cases on Hold",
        "resource": "acquisition_case",
        "action": "hold",
        "description": "Place an active acquisition case on hold.",
        "is_system_permission": True,
        "is_active": True,
    },
    {
        "code": "acquisition_case.resume",
        "name": "Resume Acquisition Cases",
        "resource": "acquisition_case",
        "action": "resume",
        "description": "Resume an acquisition case that is on hold.",
        "is_system_permission": True,
        "is_active": True,
    },
    {
        "code": "acquisition_case.cancel",
        "name": "Cancel Acquisition Cases",
        "resource": "acquisition_case",
        "action": "cancel",
        "description": "Cancel an acquisition case with a recorded reason.",
        "is_system_permission": True,
        "is_active": True,
    },
    {
        "code": "acquisition_case.close",
        "name": "Close Acquisition Cases",
        "resource": "acquisition_case",
        "action": "close",
        "description": "Close an acquisition case after completion of the required workflow.",
        "is_system_permission": True,
        "is_active": True,
    },
    {
        "code": "acquisition_case.stage_transition",
        "name": "Transition Acquisition Case Stage",
        "resource": "acquisition_case",
        "action": "stage_transition",
        "description": (
            "Advance an acquisition case through its controlled "
            "process stages."
        ),
        "is_system_permission": True,
        "is_active": True,
    },
]


ROLE_PERMISSION_CODES = {
    "acquisition_case.read": (
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
        "audit_compliance",
    ),
    "acquisition_case.create": (
        "national_administrator",
        "land_acquisition_officer",
        "project_director",
    ),
    "acquisition_case.update": (
        "national_administrator",
        "land_acquisition_officer",
        "project_director",
    ),
    "acquisition_case.activate": (
        "national_administrator",
        "land_acquisition_officer",
        "district_collector",
        "project_director",
    ),
    "acquisition_case.hold": (
        "national_administrator",
        "land_acquisition_officer",
        "district_collector",
    ),
    "acquisition_case.resume": (
        "national_administrator",
        "land_acquisition_officer",
        "district_collector",
    ),
    "acquisition_case.cancel": (
        "national_administrator",
        "district_collector",
        "project_director",
    ),
    "acquisition_case.close": (
        "national_administrator",
        "district_collector",
        "land_acquisition_officer",
    ),
    "acquisition_case.stage_transition": (
        "national_administrator",
        "land_acquisition_officer",
        "district_collector",
    ),
}


def upgrade() -> None:
    """Create acquisition-case permissions and assign baseline roles."""
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
            "Cannot assign acquisition-case permissions because these "
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
    """Remove acquisition-case permission assignments and definitions."""
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

"""add survey permissions

Revision ID: 6a7b8c9d0e12
Revises: 26b89dd4c943
Create Date: 2026-09-27
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6a7b8c9d0e12"
down_revision: Union[str, Sequence[str], None] = "26b89dd4c943"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


PERMISSIONS = [
    {
        "code": "survey.read",
        "name": "View Survey Records",
        "resource": "survey",
        "action": "read",
        "description": (
            "View and search survey and measurement records "
            "within the user's authorized scope."
        ),
        "is_system_permission": True,
        "is_active": True,
    },
    {
        "code": "survey.create",
        "name": "Create Survey Records",
        "resource": "survey",
        "action": "create",
        "description": (
            "Create and schedule survey and measurement records "
            "for authorized acquisition cases and parcels."
        ),
        "is_system_permission": True,
        "is_active": True,
    },
    {
        "code": "survey.start",
        "name": "Start Survey Work",
        "resource": "survey",
        "action": "start",
        "description": (
            "Start an authorized survey and assign the responsible "
            "surveyor where permitted."
        ),
        "is_system_permission": True,
        "is_active": True,
    },
    {
        "code": "survey.complete",
        "name": "Complete Survey Work",
        "resource": "survey",
        "action": "complete",
        "description": (
            "Record measured survey results and complete field "
            "survey work."
        ),
        "is_system_permission": True,
        "is_active": True,
    },
    {
        "code": "survey.review",
        "name": "Submit Survey for Review",
        "resource": "survey",
        "action": "review",
        "description": (
            "Submit completed survey records for formal review."
        ),
        "is_system_permission": True,
        "is_active": True,
    },
    {
        "code": "survey.verify",
        "name": "Verify Survey Records",
        "resource": "survey",
        "action": "verify",
        "description": (
            "Formally verify survey and measurement results "
            "after review."
        ),
        "is_system_permission": True,
        "is_active": True,
    },
    {
        "code": "survey.cancel",
        "name": "Cancel Survey Records",
        "resource": "survey",
        "action": "cancel",
        "description": (
            "Cancel a planned or in-progress survey with "
            "appropriate authorization."
        ),
        "is_system_permission": True,
        "is_active": True,
    },
]


ROLE_PERMISSION_CODES = {
    "survey.read": (
        "aakar_development_admin",
        "national_administrator",
        "central_ministry_officer",
        "national_monitoring_officer",
        "state_nodal_officer",
        "state_land_authority_officer",
        "state_department_officer",
        "district_collector",
        "additional_collector",
        "land_acquisition_officer",
        "revenue_officer",
        "rr_officer",
        "survey_gis_officer",
        "project_director",
        "infrastructure_officer",
        "field_verification_officer",
        "audit_compliance",
    ),
    "survey.create": (
        "aakar_development_admin",
        "national_administrator",
        "state_land_authority_officer",
        "district_collector",
        "land_acquisition_officer",
        "survey_gis_officer",
    ),
    "survey.start": (
        "aakar_development_admin",
        "national_administrator",
        "state_land_authority_officer",
        "district_collector",
        "land_acquisition_officer",
        "survey_gis_officer",
    ),
    "survey.complete": (
        "aakar_development_admin",
        "national_administrator",
        "state_land_authority_officer",
        "district_collector",
        "land_acquisition_officer",
        "survey_gis_officer",
    ),
    "survey.review": (
        "aakar_development_admin",
        "national_administrator",
        "state_land_authority_officer",
        "district_collector",
        "land_acquisition_officer",
        "survey_gis_officer",
    ),
    "survey.verify": (
        "aakar_development_admin",
        "national_administrator",
        "district_collector",
        "survey_gis_officer",
        "field_verification_officer",
    ),
    "survey.cancel": (
        "aakar_development_admin",
        "national_administrator",
        "district_collector",
        "land_acquisition_officer",
        "survey_gis_officer",
    ),
}


def upgrade() -> None:
    """Create survey permissions and assign baseline roles."""

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
            "Cannot assign survey permissions because these "
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
    """Remove survey permission assignments and definitions."""

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
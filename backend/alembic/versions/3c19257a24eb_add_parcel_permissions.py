"""add parcel permissions

Revision ID: 3c19257a24eb
Revises: 7c1f4a9e6b21
Create Date: 2026-09-26 07:42:58
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "3c19257a24eb"
down_revision = "7c1f4a9e6b21"
branch_labels = None
depends_on = None


PERMISSIONS = [
    (
        "parcel.read",
        "View parcel records",
        "parcel",
        "read",
    ),
    (
        "parcel.create",
        "Create parcel records",
        "parcel",
        "create",
    ),
    (
        "parcel.update",
        "Update parcel records",
        "parcel",
        "update",
    ),
]


ROLE_PERMISSION_CODES = {
    "aakar_development_admin": {
        "parcel.read",
        "parcel.create",
        "parcel.update",
    },
    "central_ministry_officer": {
        "parcel.read",
    },
    "state_department_officer": {
        "parcel.read",
    },
    "state_land_authority_officer": {
        "parcel.read",
        "parcel.create",
        "parcel.update",
    },
    "state_nodal_officer": {
        "parcel.read",
    },
    "district_collector": {
        "parcel.read",
        "parcel.create",
        "parcel.update",
    },
    "land_acquisition_officer": {
        "parcel.read",
        "parcel.create",
        "parcel.update",
    },
    "field_verification_officer": {
        "parcel.read",
        "parcel.update",
    },
    "survey_gis_officer": {
        "parcel.read",
        "parcel.create",
        "parcel.update",
    },
}


def upgrade() -> None:
    bind = op.get_bind()

    permission_table = sa.table(
        "permissions",
        sa.column("id", sa.UUID()),
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("resource", sa.String()),
        sa.column("action", sa.String()),
        sa.column("description", sa.String()),
    )

    role_table = sa.table(
        "roles",
        sa.column("id", sa.UUID()),
        sa.column("code", sa.String()),
        sa.column("is_active", sa.Boolean()),
    )

    role_permission_table = sa.table(
        "role_permissions",
        sa.column("role_id", sa.UUID()),
        sa.column("permission_id", sa.UUID()),
    )

    permission_ids: dict[str, object] = {}

    for code, name, resource, action in PERMISSIONS:
        existing_permission = bind.execute(
            sa.select(permission_table.c.id).where(
                permission_table.c.code == code
            )
        ).scalar_one_or_none()

        if existing_permission is None:
            bind.execute(
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
                        gen_random_uuid(),
                        :code,
                        :name,
                        :resource,
                        :action,
                        :description
                    )
                    """
                ),
                {
                    "code": code,
                    "name": name,
                    "resource": resource,
                    "action": action,
                    "description": name,
                },
            )

            existing_permission = bind.execute(
                sa.select(permission_table.c.id).where(
                    permission_table.c.code == code
                )
            ).scalar_one()

        permission_ids[code] = existing_permission

    role_codes = list(ROLE_PERMISSION_CODES.keys())

    existing_roles = bind.execute(
        sa.select(
            role_table.c.id,
            role_table.c.code,
        ).where(
            role_table.c.code.in_(role_codes),
            role_table.c.is_active.is_(True),
        )
    ).all()

    found_role_codes = {
        row.code
        for row in existing_roles
    }

    missing_role_codes = (
        set(role_codes) - found_role_codes
    )

    if missing_role_codes:
        raise RuntimeError(
            "Cannot assign parcel permissions because "
            "the following active roles are missing: "
            + ", ".join(sorted(missing_role_codes))
        )

    for role_id, role_code in existing_roles:
        for permission_code in ROLE_PERMISSION_CODES[
            role_code
        ]:
            permission_id = permission_ids[
                permission_code
            ]

            bind.execute(
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
                    ON CONFLICT (
                        role_id,
                        permission_id
                    )
                    DO NOTHING
                    """
                ),
                {
                    "role_id": role_id,
                    "permission_id": permission_id,
                },
            )


def downgrade() -> None:
    bind = op.get_bind()

    permission_codes = [
        code
        for code, _, _, _ in PERMISSIONS
    ]

    permission_ids = bind.execute(
        sa.text(
            """
            SELECT id
            FROM permissions
            WHERE code = ANY(:codes)
            """
        ),
        {"codes": permission_codes},
    ).scalars().all()

    if permission_ids:
        bind.execute(
            sa.text(
                """
                DELETE FROM role_permissions
                WHERE permission_id = ANY(:permission_ids)
                """
            ),
            {"permission_ids": permission_ids},
        )

    bind.execute(
        sa.text(
            """
            DELETE FROM permissions
            WHERE code = ANY(:codes)
            """
        ),
        {"codes": permission_codes},
    )
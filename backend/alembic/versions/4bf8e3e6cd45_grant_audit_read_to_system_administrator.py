"""grant audit read to system administrator

Revision ID: 4bf8e3e6cd45
Revises: 0dc0831e7e03
Create Date: 2026-09-21
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "4bf8e3e6cd45"
down_revision = "0dc0831e7e03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    role_id_query = sa.text(
        """
        SELECT id
        FROM roles
        WHERE code = 'system_administrator'
          AND is_active = TRUE
        """
    )

    permission_id_query = sa.text(
        """
        SELECT id
        FROM permissions
        WHERE code = 'audit.read'
          AND is_active = TRUE
        """
    )

    connection = op.get_bind()

    role_id = connection.execute(role_id_query).scalar_one_or_none()
    permission_id = connection.execute(
        permission_id_query
    ).scalar_one_or_none()

    if role_id is None:
        raise RuntimeError(
            "Active system_administrator role was not found."
        )

    if permission_id is None:
        raise RuntimeError(
            "Active audit.read permission was not found."
        )

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
    connection = op.get_bind()

    connection.execute(
        sa.text(
            """
            DELETE FROM role_permissions
            WHERE role_id = (
                SELECT id
                FROM roles
                WHERE code = 'system_administrator'
            )
            AND permission_id = (
                SELECT id
                FROM permissions
                WHERE code = 'audit.read'
            )
            """
        )
    )
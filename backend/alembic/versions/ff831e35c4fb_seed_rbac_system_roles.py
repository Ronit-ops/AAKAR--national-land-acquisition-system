"""seed RBAC system roles

Revision ID: ff831e35c4fb
Revises: d4c6152421e4
Create Date: 2026-09-18 12:03:28.791231

"""

from typing import Sequence, Union
from uuid import UUID

from alembic import op
import sqlalchemy as sa


revision: str = "ff831e35c4fb"
down_revision: Union[str, Sequence[str], None] = "d4c6152421e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ROLE_TABLE = sa.table(
    "roles",
    sa.column("id", sa.Uuid()),
    sa.column("code", sa.String(length=80)),
    sa.column("name", sa.String(length=150)),
    sa.column("scope_level", sa.String(length=30)),
    sa.column("description", sa.Text()),
    sa.column("is_system_role", sa.Boolean()),
    sa.column("is_active", sa.Boolean()),
)


ROLE_SEEDS = [
    {
        "id": UUID("00000000-0000-4000-8000-000000000001"),
        "code": "national_administrator",
        "name": "National Administrator",
        "scope_level": "national",
        "description": "System role for national-level platform administration.",
        "is_system_role": True,
        "is_active": True,
    },
    {
        "id": UUID("00000000-0000-4000-8000-000000000002"),
        "code": "central_ministry_officer",
        "name": "Central Ministry Officer",
        "scope_level": "national",
        "description": "Officer role for authorized central ministry operations.",
        "is_system_role": True,
        "is_active": True,
    },
    {
        "id": UUID("00000000-0000-4000-8000-000000000003"),
        "code": "national_monitoring_officer",
        "name": "National Monitoring Officer",
        "scope_level": "national",
        "description": "Role for national monitoring and decision-support views.",
        "is_system_role": True,
        "is_active": True,
    },
    {
        "id": UUID("00000000-0000-4000-8000-000000000004"),
        "code": "state_nodal_officer",
        "name": "State Nodal Officer",
        "scope_level": "state",
        "description": "State-level nodal role for coordination and monitoring.",
        "is_system_role": True,
        "is_active": True,
    },
    {
        "id": UUID("00000000-0000-4000-8000-000000000005"),
        "code": "state_land_authority_officer",
        "name": "State Land Authority Officer",
        "scope_level": "state",
        "description": "State-level role for land acquisition authority operations.",
        "is_system_role": True,
        "is_active": True,
    },
    {
        "id": UUID("00000000-0000-4000-8000-000000000006"),
        "code": "state_department_officer",
        "name": "State Department Officer",
        "scope_level": "state",
        "description": "State department role for authorized land-program operations.",
        "is_system_role": True,
        "is_active": True,
    },
    {
        "id": UUID("00000000-0000-4000-8000-000000000007"),
        "code": "district_collector",
        "name": "District Collector",
        "scope_level": "district",
        "description": "District-level administrative and acquisition oversight role.",
        "is_system_role": True,
        "is_active": True,
    },
    {
        "id": UUID("00000000-0000-4000-8000-000000000008"),
        "code": "additional_collector",
        "name": "Additional Collector",
        "scope_level": "district",
        "description": "District-level administrative role supporting collector functions.",
        "is_system_role": True,
        "is_active": True,
    },
    {
        "id": UUID("00000000-0000-4000-8000-000000000009"),
        "code": "land_acquisition_officer",
        "name": "Land Acquisition Officer",
        "scope_level": "district",
        "description": "Operational role for land acquisition case processing.",
        "is_system_role": True,
        "is_active": True,
    },
    {
        "id": UUID("00000000-0000-4000-8000-000000000010"),
        "code": "revenue_officer",
        "name": "Revenue Officer",
        "scope_level": "district",
        "description": "Role for authorized revenue and land-record operations.",
        "is_system_role": True,
        "is_active": True,
    },
    {
        "id": UUID("00000000-0000-4000-8000-000000000011"),
        "code": "rr_officer",
        "name": "R&R Officer",
        "scope_level": "district",
        "description": "Role for authorized rehabilitation and resettlement operations.",
        "is_system_role": True,
        "is_active": True,
    },
    {
        "id": UUID("00000000-0000-4000-8000-000000000012"),
        "code": "survey_gis_officer",
        "name": "Survey/GIS Officer",
        "scope_level": "district",
        "description": "Role for survey and GIS-related operational work.",
        "is_system_role": True,
        "is_active": True,
    },
    {
        "id": UUID("00000000-0000-4000-8000-000000000013"),
        "code": "project_director",
        "name": "Project Director",
        "scope_level": "project",
        "description": "Project-level role for land requirement and implementation oversight.",
        "is_system_role": True,
        "is_active": True,
    },
    {
        "id": UUID("00000000-0000-4000-8000-000000000014"),
        "code": "infrastructure_officer",
        "name": "Infrastructure Officer",
        "scope_level": "project",
        "description": "Project-level role for implementation-related operations.",
        "is_system_role": True,
        "is_active": True,
    },
    {
        "id": UUID("00000000-0000-4000-8000-000000000015"),
        "code": "field_verification_officer",
        "name": "Field Verification Officer",
        "scope_level": "project",
        "description": "Role for authorized field verification activities.",
        "is_system_role": True,
        "is_active": True,
    },
    {
        "id": UUID("00000000-0000-4000-8000-000000000016"),
        "code": "landowner_recorded_right_holder",
        "name": "Landowner / Recorded Right Holder",
        "scope_level": "citizen",
        "description": "Citizen-facing role for an authorized recorded right-holder view.",
        "is_system_role": True,
        "is_active": True,
    },
    {
        "id": UUID("00000000-0000-4000-8000-000000000017"),
        "code": "affected_family",
        "name": "Affected Family",
        "scope_level": "citizen",
        "description": "Citizen-facing role for an affected family member.",
        "is_system_role": True,
        "is_active": True,
    },
    {
        "id": UUID("00000000-0000-4000-8000-000000000018"),
        "code": "authorized_representative",
        "name": "Authorized Representative",
        "scope_level": "citizen",
        "description": "Citizen-facing role for an authorized representative.",
        "is_system_role": True,
        "is_active": True,
    },
    {
        "id": UUID("00000000-0000-4000-8000-000000000019"),
        "code": "system_administrator",
        "name": "System Administrator",
        "scope_level": "system",
        "description": "Technical administration role for authorized platform operations.",
        "is_system_role": True,
        "is_active": True,
    },
    {
        "id": UUID("00000000-0000-4000-8000-000000000020"),
        "code": "audit_compliance",
        "name": "Audit/Compliance",
        "scope_level": "system",
        "description": "Role for authorized audit and compliance activities.",
        "is_system_role": True,
        "is_active": True,
    },
]


def upgrade() -> None:
    """Seed the baseline AAKAR system roles."""
    op.bulk_insert(
        ROLE_TABLE,
        ROLE_SEEDS,
    )


def downgrade() -> None:
    """Remove the baseline AAKAR system roles."""
    op.execute(
        sa.text(
            """
            DELETE FROM roles
            WHERE code IN (
                'national_administrator',
                'central_ministry_officer',
                'national_monitoring_officer',
                'state_nodal_officer',
                'state_land_authority_officer',
                'state_department_officer',
                'district_collector',
                'additional_collector',
                'land_acquisition_officer',
                'revenue_officer',
                'rr_officer',
                'survey_gis_officer',
                'project_director',
                'infrastructure_officer',
                'field_verification_officer',
                'landowner_recorded_right_holder',
                'affected_family',
                'authorized_representative',
                'system_administrator',
                'audit_compliance'
            )
            """
        )
    )
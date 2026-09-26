"""refine acquisition case domain

Revision ID: 2e8f5fa53393
Revises: 5b7c91d8e4f2
Create Date: 2026-09-25 23:13:43.016149

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2e8f5fa53393"
down_revision: Union[str, Sequence[str], None] = "5b7c91d8e4f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Refine the acquisition-case domain for AR-003.

    This migration:
    1. Removes the legacy acquisition-case CHECK constraints.
    2. Adds legal framework, acquisition method and optimistic-lock version.
    3. Refines stage/status/legal-route column lengths.
    4. Removes the obsolete case_type field.
    5. Installs the new controlled-value CHECK constraints.
    6. Adds indexes for legal framework and acquisition method.

    The current database contains no acquisition cases or stage-history
    records, so no legacy row-value migration is required.
    """

    # ------------------------------------------------------------------
    # 1. Remove legacy CHECK constraints
    # ------------------------------------------------------------------

    # These names are the actual PostgreSQL constraint names currently
    # present in the database.

    op.drop_constraint(
        op.f("ck_acquisition_cases_ck_acquisition_cases_case_type"),
        "acquisition_cases",
        type_="check",
    )

    op.drop_constraint(
        op.f("ck_acquisition_cases_ck_acquisition_cases_status"),
        "acquisition_cases",
        type_="check",
    )

    op.drop_constraint(
        op.f("ck_acquisition_cases_ck_acquisition_cases_current_stage"),
        "acquisition_cases",
        type_="check",
    )

    op.drop_constraint(
        op.f("ck_acquisition_case_stage_history_ck_case_stage_history_264a"),
        "acquisition_case_stage_history",
        type_="check",
    )

    op.drop_constraint(
        op.f("ck_acquisition_case_stage_history_ck_case_stage_history_481b"),
        "acquisition_case_stage_history",
        type_="check",
    )

    # ------------------------------------------------------------------
    # 2. Add new acquisition-case columns
    # ------------------------------------------------------------------

    op.add_column(
        "acquisition_cases",
        sa.Column(
            "legal_framework",
            sa.String(length=40),
            server_default=sa.text("'RFCTLARR_2013'"),
            nullable=False,
        ),
    )

    op.add_column(
        "acquisition_cases",
        sa.Column(
            "acquisition_method",
            sa.String(length=40),
            server_default=sa.text("'COMPULSORY_ACQUISITION'"),
            nullable=False,
        ),
    )

    op.add_column(
        "acquisition_cases",
        sa.Column(
            "version",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),
    )

    # ------------------------------------------------------------------
    # 3. Refine existing column lengths
    # ------------------------------------------------------------------

    op.alter_column(
        "acquisition_case_stage_history",
        "from_stage",
        existing_type=sa.VARCHAR(length=40),
        type_=sa.String(length=50),
        existing_nullable=True,
    )

    op.alter_column(
        "acquisition_case_stage_history",
        "to_stage",
        existing_type=sa.VARCHAR(length=40),
        type_=sa.String(length=50),
        existing_nullable=False,
    )

    op.alter_column(
        "acquisition_cases",
        "legal_route",
        existing_type=sa.VARCHAR(length=150),
        type_=sa.String(length=50),
        existing_nullable=True,
    )

    op.alter_column(
        "acquisition_cases",
        "status",
        existing_type=sa.VARCHAR(length=30),
        type_=sa.String(length=20),
        existing_nullable=False,
        existing_server_default=sa.text("'DRAFT'::character varying"),
    )

    op.alter_column(
        "acquisition_cases",
        "current_stage",
        existing_type=sa.VARCHAR(length=40),
        type_=sa.String(length=50),
        existing_nullable=False,
        existing_server_default=sa.text("'PROPOSAL'::character varying"),
    )

    # ------------------------------------------------------------------
    # 4. Remove obsolete case_type
    # ------------------------------------------------------------------

    op.drop_column(
        "acquisition_cases",
        "case_type",
    )

    # ------------------------------------------------------------------
    # 5. Update server defaults
    # ------------------------------------------------------------------

    op.alter_column(
        "acquisition_cases",
        "current_stage",
        server_default=sa.text("'INITIATION'"),
    )

    op.alter_column(
        "acquisition_cases",
        "status",
        server_default=sa.text("'DRAFT'"),
    )

    # ------------------------------------------------------------------
    # 6. Add new CHECK constraints
    #
    # op.f() is used so Alembic applies the project's naming convention
    # consistently with the existing schema.
    # ------------------------------------------------------------------

    op.create_check_constraint(
        op.f("ck_acquisition_cases_ck_acquisition_cases_legal_framework"),
        "acquisition_cases",
        """
        legal_framework IN (
            'RFCTLARR_2013',
            'SPECIAL_CENTRAL_ACT',
            'STATE_LAW',
            'OTHER'
        )
        """,
    )

    op.create_check_constraint(
        op.f("ck_acquisition_cases_ck_acquisition_cases_legal_route"),
        "acquisition_cases",
        """
        legal_route IS NULL OR legal_route IN (
            'RFCTLARR_STANDARD',
            'RFCTLARR_URGENT',
            'SPECIAL_ACT_ROUTE',
            'STATE_SPECIFIC_ROUTE',
            'NEGOTIATED_PURCHASE'
        )
        """,
    )

    op.create_check_constraint(
        op.f("ck_acquisition_cases_ck_acquisition_cases_acquisition_method"),
        "acquisition_cases",
        """
        acquisition_method IN (
            'COMPULSORY_ACQUISITION',
            'CONSENT_BASED',
            'NEGOTIATED_PURCHASE'
        )
        """,
    )

    op.create_check_constraint(
        op.f("ck_acquisition_cases_ck_acquisition_cases_status"),
        "acquisition_cases",
        """
        status IN (
            'DRAFT',
            'ACTIVE',
            'ON_HOLD',
            'CANCELLED',
            'CLOSED'
        )
        """,
    )

    op.create_check_constraint(
        op.f("ck_acquisition_cases_ck_acquisition_cases_current_stage"),
        "acquisition_cases",
        """
        current_stage IN (
            'INITIATION',
            'SIA',
            'PRELIMINARY_NOTIFICATION',
            'OBJECTIONS_AND_HEARING',
            'DECLARATION',
            'R_AND_R',
            'CLAIMS_AND_ENQUIRY',
            'COMPENSATION_DETERMINATION',
            'AWARD',
            'COMPENSATION_AND_RR',
            'POSSESSION',
            'VESTING',
            'HANDOVER'
        )
        """,
    )

    op.create_check_constraint(
        op.f("ck_acquisition_cases_ck_acquisition_cases_version_positive"),
        "acquisition_cases",
        "version >= 1",
    )

    op.create_check_constraint(
        op.f(
            "ck_acquisition_case_stage_history_ck_case_stage_history_from_stage"
        ),
        "acquisition_case_stage_history",
        """
        from_stage IS NULL OR from_stage IN (
            'INITIATION',
            'SIA',
            'PRELIMINARY_NOTIFICATION',
            'OBJECTIONS_AND_HEARING',
            'DECLARATION',
            'R_AND_R',
            'CLAIMS_AND_ENQUIRY',
            'COMPENSATION_DETERMINATION',
            'AWARD',
            'COMPENSATION_AND_RR',
            'POSSESSION',
            'VESTING',
            'HANDOVER'
        )
        """,
    )

    op.create_check_constraint(
        op.f(
            "ck_acquisition_case_stage_history_ck_case_stage_history_to_stage"
        ),
        "acquisition_case_stage_history",
        """
        to_stage IN (
            'INITIATION',
            'SIA',
            'PRELIMINARY_NOTIFICATION',
            'OBJECTIONS_AND_HEARING',
            'DECLARATION',
            'R_AND_R',
            'CLAIMS_AND_ENQUIRY',
            'COMPENSATION_DETERMINATION',
            'AWARD',
            'COMPENSATION_AND_RR',
            'POSSESSION',
            'VESTING',
            'HANDOVER'
        )
        """,
    )

    # ------------------------------------------------------------------
    # 7. Add indexes
    # ------------------------------------------------------------------

    op.create_index(
        "ix_acquisition_cases_acquisition_method",
        "acquisition_cases",
        ["acquisition_method"],
        unique=False,
    )

    op.create_index(
        "ix_acquisition_cases_legal_framework",
        "acquisition_cases",
        ["legal_framework"],
        unique=False,
    )


def downgrade() -> None:
    """
    Reverse the AR-003 acquisition-case domain refinement.

    This downgrade restores the previous schema vocabulary.
    """

    # ------------------------------------------------------------------
    # 1. Remove refined CHECK constraints
    # ------------------------------------------------------------------

    op.drop_constraint(
        op.f(
            "ck_acquisition_case_stage_history_ck_case_stage_history_to_stage"
        ),
        "acquisition_case_stage_history",
        type_="check",
    )

    op.drop_constraint(
        op.f(
            "ck_acquisition_case_stage_history_ck_case_stage_history_from_stage"
        ),
        "acquisition_case_stage_history",
        type_="check",
    )

    op.drop_constraint(
        op.f("ck_acquisition_cases_ck_acquisition_cases_version_positive"),
        "acquisition_cases",
        type_="check",
    )

    op.drop_constraint(
        op.f("ck_acquisition_cases_ck_acquisition_cases_current_stage"),
        "acquisition_cases",
        type_="check",
    )

    op.drop_constraint(
        op.f("ck_acquisition_cases_ck_acquisition_cases_status"),
        "acquisition_cases",
        type_="check",
    )

    op.drop_constraint(
        op.f("ck_acquisition_cases_ck_acquisition_cases_acquisition_method"),
        "acquisition_cases",
        type_="check",
    )

    op.drop_constraint(
        op.f("ck_acquisition_cases_ck_acquisition_cases_legal_route"),
        "acquisition_cases",
        type_="check",
    )

    op.drop_constraint(
        op.f("ck_acquisition_cases_ck_acquisition_cases_legal_framework"),
        "acquisition_cases",
        type_="check",
    )

    # ------------------------------------------------------------------
    # 2. Restore case_type
    # ------------------------------------------------------------------

    op.add_column(
        "acquisition_cases",
        sa.Column(
            "case_type",
            sa.VARCHAR(length=30),
            server_default=sa.text("'STATUTORY'::character varying"),
            nullable=False,
        ),
    )

    # Existing refined records are mapped back to the legacy categories.
    op.execute(
        """
        UPDATE acquisition_cases
        SET case_type = CASE
            WHEN acquisition_method = 'NEGOTIATED_PURCHASE'
                THEN 'NEGOTIATED'
            WHEN acquisition_method = 'CONSENT_BASED'
                THEN 'NEGOTIATED'
            ELSE 'STATUTORY'
        END
        """
    )

    # ------------------------------------------------------------------
    # 3. Restore legacy stage vocabulary
    # ------------------------------------------------------------------

    op.execute(
        """
        UPDATE acquisition_cases
        SET current_stage = CASE current_stage
            WHEN 'INITIATION' THEN 'PROPOSAL'
            WHEN 'SIA' THEN 'SIA'
            WHEN 'PRELIMINARY_NOTIFICATION' THEN 'NOTIFICATION'
            WHEN 'OBJECTIONS_AND_HEARING' THEN 'OBJECTIONS'
            WHEN 'DECLARATION' THEN 'DECLARATION'
            WHEN 'R_AND_R' THEN 'R_AND_R'
            WHEN 'CLAIMS_AND_ENQUIRY' THEN 'CLAIMS_VERIFICATION'
            WHEN 'COMPENSATION_DETERMINATION' THEN 'VALUATION'
            WHEN 'AWARD' THEN 'AWARD'
            WHEN 'COMPENSATION_AND_RR' THEN 'COMPENSATION'
            WHEN 'POSSESSION' THEN 'POSSESSION'
            WHEN 'VESTING' THEN 'POSSESSION'
            WHEN 'HANDOVER' THEN 'HANDOVER'
            ELSE 'PROPOSAL'
        END
        """
    )

    op.execute(
        """
        UPDATE acquisition_case_stage_history
        SET from_stage = CASE from_stage
            WHEN 'INITIATION' THEN 'PROPOSAL'
            WHEN 'SIA' THEN 'SIA'
            WHEN 'PRELIMINARY_NOTIFICATION' THEN 'NOTIFICATION'
            WHEN 'OBJECTIONS_AND_HEARING' THEN 'OBJECTIONS'
            WHEN 'DECLARATION' THEN 'DECLARATION'
            WHEN 'R_AND_R' THEN 'R_AND_R'
            WHEN 'CLAIMS_AND_ENQUIRY' THEN 'CLAIMS_VERIFICATION'
            WHEN 'COMPENSATION_DETERMINATION' THEN 'VALUATION'
            WHEN 'AWARD' THEN 'AWARD'
            WHEN 'COMPENSATION_AND_RR' THEN 'COMPENSATION'
            WHEN 'POSSESSION' THEN 'POSSESSION'
            WHEN 'VESTING' THEN 'POSSESSION'
            WHEN 'HANDOVER' THEN 'HANDOVER'
            ELSE 'PROPOSAL'
        END
        """
    )

    op.execute(
        """
        UPDATE acquisition_case_stage_history
        SET to_stage = CASE to_stage
            WHEN 'INITIATION' THEN 'PROPOSAL'
            WHEN 'SIA' THEN 'SIA'
            WHEN 'PRELIMINARY_NOTIFICATION' THEN 'NOTIFICATION'
            WHEN 'OBJECTIONS_AND_HEARING' THEN 'OBJECTIONS'
            WHEN 'DECLARATION' THEN 'DECLARATION'
            WHEN 'R_AND_R' THEN 'R_AND_R'
            WHEN 'CLAIMS_AND_ENQUIRY' THEN 'CLAIMS_VERIFICATION'
            WHEN 'COMPENSATION_DETERMINATION' THEN 'VALUATION'
            WHEN 'AWARD' THEN 'AWARD'
            WHEN 'COMPENSATION_AND_RR' THEN 'COMPENSATION'
            WHEN 'POSSESSION' THEN 'POSSESSION'
            WHEN 'VESTING' THEN 'POSSESSION'
            WHEN 'HANDOVER' THEN 'HANDOVER'
            ELSE 'PROPOSAL'
        END
        """
    )

    # ------------------------------------------------------------------
    # 4. Restore legacy status vocabulary
    # ------------------------------------------------------------------

    op.execute(
        """
        UPDATE acquisition_cases
        SET status = CASE status
            WHEN 'ACTIVE' THEN 'APPROVED'
            WHEN 'ON_HOLD' THEN 'ACTION_REQUIRED'
            WHEN 'CANCELLED' THEN 'REJECTED'
            WHEN 'CLOSED' THEN 'COMPLETED'
            ELSE status
        END
        """
    )

    # ------------------------------------------------------------------
    # 5. Restore legacy CHECK constraints
    # ------------------------------------------------------------------

    op.create_check_constraint(
        op.f("ck_acquisition_cases_ck_acquisition_cases_case_type"),
        "acquisition_cases",
        """
        case_type IN (
            'STATUTORY',
            'NEGOTIATED',
            'OTHER'
        )
        """,
    )

    op.create_check_constraint(
        op.f("ck_acquisition_cases_ck_acquisition_cases_status"),
        "acquisition_cases",
        """
        status IN (
            'DRAFT',
            'IN_REVIEW',
            'ACTION_REQUIRED',
            'APPROVED',
            'REJECTED',
            'COMPLETED'
        )
        """,
    )

    op.create_check_constraint(
        op.f("ck_acquisition_cases_ck_acquisition_cases_current_stage"),
        "acquisition_cases",
        """
        current_stage IN (
            'PROPOSAL',
            'SCRUTINY',
            'SIA',
            'NOTIFICATION',
            'SURVEY',
            'OBJECTIONS',
            'DECLARATION',
            'CLAIMS_VERIFICATION',
            'VALUATION',
            'AWARD',
            'COMPENSATION',
            'R_AND_R',
            'POSSESSION',
            'HANDOVER',
            'DISPUTE',
            'CLOSURE'
        )
        """,
    )

    op.create_check_constraint(
        op.f(
            "ck_acquisition_case_stage_history_ck_case_stage_history_from_stage"
        ),
        "acquisition_case_stage_history",
        """
        from_stage IS NULL OR from_stage IN (
            'PROPOSAL',
            'SCRUTINY',
            'SIA',
            'NOTIFICATION',
            'SURVEY',
            'OBJECTIONS',
            'DECLARATION',
            'CLAIMS_VERIFICATION',
            'VALUATION',
            'AWARD',
            'COMPENSATION',
            'R_AND_R',
            'POSSESSION',
            'HANDOVER',
            'DISPUTE',
            'CLOSURE'
        )
        """,
    )

    op.create_check_constraint(
        op.f(
            "ck_acquisition_case_stage_history_ck_case_stage_history_to_stage"
        ),
        "acquisition_case_stage_history",
        """
        to_stage IN (
            'PROPOSAL',
            'SCRUTINY',
            'SIA',
            'NOTIFICATION',
            'SURVEY',
            'OBJECTIONS',
            'DECLARATION',
            'CLAIMS_VERIFICATION',
            'VALUATION',
            'AWARD',
            'COMPENSATION',
            'R_AND_R',
            'POSSESSION',
            'HANDOVER',
            'DISPUTE',
            'CLOSURE'
        )
        """,
    )

    # ------------------------------------------------------------------
    # 6. Remove new indexes
    # ------------------------------------------------------------------

    op.drop_index(
        "ix_acquisition_cases_legal_framework",
        table_name="acquisition_cases",
    )

    op.drop_index(
        "ix_acquisition_cases_acquisition_method",
        table_name="acquisition_cases",
    )

    # ------------------------------------------------------------------
    # 7. Restore old defaults
    # ------------------------------------------------------------------

    op.alter_column(
        "acquisition_cases",
        "current_stage",
        server_default=sa.text("'PROPOSAL'"),
    )

    op.alter_column(
        "acquisition_cases",
        "status",
        server_default=sa.text("'DRAFT'"),
    )

    # ------------------------------------------------------------------
    # 8. Remove refined columns
    # ------------------------------------------------------------------

    op.drop_column(
        "acquisition_cases",
        "version",
    )

    op.drop_column(
        "acquisition_cases",
        "acquisition_method",
    )

    op.drop_column(
        "acquisition_cases",
        "legal_framework",
    )

    # ------------------------------------------------------------------
    # 9. Restore original column lengths
    # ------------------------------------------------------------------

    op.alter_column(
        "acquisition_cases",
        "legal_route",
        existing_type=sa.String(length=50),
        type_=sa.VARCHAR(length=150),
        existing_nullable=True,
    )

    op.alter_column(
        "acquisition_cases",
        "status",
        existing_type=sa.String(length=20),
        type_=sa.VARCHAR(length=30),
        existing_nullable=False,
        existing_server_default=sa.text("'DRAFT'::character varying"),
    )

    op.alter_column(
        "acquisition_cases",
        "current_stage",
        existing_type=sa.String(length=50),
        type_=sa.VARCHAR(length=40),
        existing_nullable=False,
        existing_server_default=sa.text("'PROPOSAL'::character varying"),
    )

    op.alter_column(
        "acquisition_case_stage_history",
        "to_stage",
        existing_type=sa.String(length=50),
        type_=sa.VARCHAR(length=40),
        existing_nullable=False,
    )

    op.alter_column(
        "acquisition_case_stage_history",
        "from_stage",
        existing_type=sa.String(length=50),
        type_=sa.VARCHAR(length=40),
        existing_nullable=True,
    )

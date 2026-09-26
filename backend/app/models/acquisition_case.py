from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


# ---------------------------------------------------------------------------
# Controlled domain values
# ---------------------------------------------------------------------------

LEGAL_FRAMEWORKS = (
    "RFCTLARR_2013",
    "SPECIAL_CENTRAL_ACT",
    "STATE_LAW",
    "OTHER",
)

LEGAL_ROUTES = (
    "RFCTLARR_STANDARD",
    "RFCTLARR_URGENT",
    "SPECIAL_ACT_ROUTE",
    "STATE_SPECIFIC_ROUTE",
    "NEGOTIATED_PURCHASE",
)

ACQUISITION_METHODS = (
    "COMPULSORY_ACQUISITION",
    "CONSENT_BASED",
    "NEGOTIATED_PURCHASE",
)

CASE_STATUSES = (
    "DRAFT",
    "ACTIVE",
    "ON_HOLD",
    "CANCELLED",
    "CLOSED",
)

CASE_STAGES = (
    "INITIATION",
    "SIA",
    "PRELIMINARY_NOTIFICATION",
    "OBJECTIONS_AND_HEARING",
    "DECLARATION",
    "R_AND_R",
    "CLAIMS_AND_ENQUIRY",
    "COMPENSATION_DETERMINATION",
    "AWARD",
    "COMPENSATION_AND_RR",
    "POSSESSION",
    "VESTING",
    "HANDOVER",
)


# ---------------------------------------------------------------------------
# Acquisition Case
# ---------------------------------------------------------------------------


class AcquisitionCase(Base):
    """
    Central workflow container for a land acquisition process.

    This model intentionally contains only case-level workflow information.
    Detailed statutory modules such as notifications, objections, valuation,
    award, compensation, R&R, possession and handover are modeled separately.
    """

    __tablename__ = "acquisition_cases"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    # -----------------------------------------------------------------------
    # Parent land requirement
    # -----------------------------------------------------------------------

    land_requirement_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "land_requirements.id",
        ),
        nullable=False,
    )

    # -----------------------------------------------------------------------
    # Human-readable immutable case reference
    # -----------------------------------------------------------------------

    case_number: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
    )

    # -----------------------------------------------------------------------
    # Legal framework / route / acquisition method
    # -----------------------------------------------------------------------

    legal_framework: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default="RFCTLARR_2013",
        server_default="RFCTLARR_2013",
    )

    legal_route: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    acquisition_method: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default="COMPULSORY_ACQUISITION",
        server_default="COMPULSORY_ACQUISITION",
    )

    # -----------------------------------------------------------------------
    # Responsibility
    # -----------------------------------------------------------------------

    responsible_authority_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "authorities.id",
        ),
        nullable=True,
    )

    assigned_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "users.id",
        ),
        nullable=True,
    )

    # -----------------------------------------------------------------------
    # Operational case status
    # -----------------------------------------------------------------------

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="DRAFT",
        server_default="DRAFT",
    )

    # -----------------------------------------------------------------------
    # Current statutory/process stage
    # -----------------------------------------------------------------------

    current_stage: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="INITIATION",
        server_default="INITIATION",
    )

    # -----------------------------------------------------------------------
    # Free-form case description
    # -----------------------------------------------------------------------

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # -----------------------------------------------------------------------
    # Lifecycle timestamps
    # -----------------------------------------------------------------------

    opened_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # -----------------------------------------------------------------------
    # Optimistic concurrency
    # -----------------------------------------------------------------------

    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )

    # -----------------------------------------------------------------------
    # Audit timestamps
    # -----------------------------------------------------------------------

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # -----------------------------------------------------------------------
    # Relationships
    # -----------------------------------------------------------------------

    land_requirement: Mapped["LandRequirement"] = relationship(
        back_populates="acquisition_cases",
    )

    stage_history: Mapped[list["AcquisitionCaseStageHistory"]] = relationship(
        back_populates="acquisition_case",
        cascade="all, delete-orphan",
        order_by="AcquisitionCaseStageHistory.changed_at",
    )

    case_parcels: Mapped[list["CaseParcel"]] = relationship(
        back_populates="acquisition_case",
        cascade="all, delete-orphan",
    )

    # -----------------------------------------------------------------------
    # Database constraints / indexes
    # -----------------------------------------------------------------------

    __table_args__ = (
        UniqueConstraint(
            "case_number",
            name="uq_acquisition_cases_case_number",
        ),

        CheckConstraint(
            "legal_framework IN ("
            "'RFCTLARR_2013', "
            "'SPECIAL_CENTRAL_ACT', "
            "'STATE_LAW', "
            "'OTHER'"
            ")",
            name="ck_acquisition_cases_legal_framework",
        ),

        CheckConstraint(
            "legal_route IS NULL OR legal_route IN ("
            "'RFCTLARR_STANDARD', "
            "'RFCTLARR_URGENT', "
            "'SPECIAL_ACT_ROUTE', "
            "'STATE_SPECIFIC_ROUTE', "
            "'NEGOTIATED_PURCHASE'"
            ")",
            name="ck_acquisition_cases_legal_route",
        ),

        CheckConstraint(
            "acquisition_method IN ("
            "'COMPULSORY_ACQUISITION', "
            "'CONSENT_BASED', "
            "'NEGOTIATED_PURCHASE'"
            ")",
            name="ck_acquisition_cases_acquisition_method",
        ),

        CheckConstraint(
            "status IN ("
            "'DRAFT', "
            "'ACTIVE', "
            "'ON_HOLD', "
            "'CANCELLED', "
            "'CLOSED'"
            ")",
            name="ck_acquisition_cases_status",
        ),

        CheckConstraint(
            "current_stage IN ("
            "'INITIATION', "
            "'SIA', "
            "'PRELIMINARY_NOTIFICATION', "
            "'OBJECTIONS_AND_HEARING', "
            "'DECLARATION', "
            "'R_AND_R', "
            "'CLAIMS_AND_ENQUIRY', "
            "'COMPENSATION_DETERMINATION', "
            "'AWARD', "
            "'COMPENSATION_AND_RR', "
            "'POSSESSION', "
            "'VESTING', "
            "'HANDOVER'"
            ")",
            name="ck_acquisition_cases_current_stage",
        ),

        CheckConstraint(
            "version >= 1",
            name="ck_acquisition_cases_version_positive",
        ),

        Index(
            "ix_acquisition_cases_land_requirement_id",
            "land_requirement_id",
        ),

        Index(
            "ix_acquisition_cases_status",
            "status",
        ),

        Index(
            "ix_acquisition_cases_current_stage",
            "current_stage",
        ),

        Index(
            "ix_acquisition_cases_responsible_authority_id",
            "responsible_authority_id",
        ),

        Index(
            "ix_acquisition_cases_legal_framework",
            "legal_framework",
        ),

        Index(
            "ix_acquisition_cases_acquisition_method",
            "acquisition_method",
        ),
    )


# ---------------------------------------------------------------------------
# Acquisition Case Stage History
# ---------------------------------------------------------------------------


class AcquisitionCaseStageHistory(Base):
    """
    Immutable history of acquisition case stage transitions.

    Stage changes must be performed through the acquisition-case service.
    """

    __tablename__ = "acquisition_case_stage_history"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    acquisition_case_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "acquisition_cases.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    from_stage: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    to_stage: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    changed_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "users.id",
        ),
        nullable=True,
    )

    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    acquisition_case: Mapped["AcquisitionCase"] = relationship(
        back_populates="stage_history",
    )

    __table_args__ = (
        CheckConstraint(
            "from_stage IS NULL OR from_stage IN ("
            "'INITIATION', "
            "'SIA', "
            "'PRELIMINARY_NOTIFICATION', "
            "'OBJECTIONS_AND_HEARING', "
            "'DECLARATION', "
            "'R_AND_R', "
            "'CLAIMS_AND_ENQUIRY', "
            "'COMPENSATION_DETERMINATION', "
            "'AWARD', "
            "'COMPENSATION_AND_RR', "
            "'POSSESSION', "
            "'VESTING', "
            "'HANDOVER'"
            ")",
            name="ck_case_stage_history_from_stage",
        ),

        CheckConstraint(
            "to_stage IN ("
            "'INITIATION', "
            "'SIA', "
            "'PRELIMINARY_NOTIFICATION', "
            "'OBJECTIONS_AND_HEARING', "
            "'DECLARATION', "
            "'R_AND_R', "
            "'CLAIMS_AND_ENQUIRY', "
            "'COMPENSATION_DETERMINATION', "
            "'AWARD', "
            "'COMPENSATION_AND_RR', "
            "'POSSESSION', "
            "'VESTING', "
            "'HANDOVER'"
            ")",
            name="ck_case_stage_history_to_stage",
        ),

        Index(
            "ix_case_stage_history_case_id_changed_at",
            "acquisition_case_id",
            "changed_at",
        ),
    )
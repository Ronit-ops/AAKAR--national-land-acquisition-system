from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


CASE_STAGES = (
    "PROPOSAL",
    "SCRUTINY",
    "SIA",
    "NOTIFICATION",
    "SURVEY",
    "OBJECTIONS",
    "DECLARATION",
    "CLAIMS_VERIFICATION",
    "VALUATION",
    "AWARD",
    "COMPENSATION",
    "R_AND_R",
    "POSSESSION",
    "HANDOVER",
    "DISPUTE",
    "CLOSURE",
)

CASE_STATUSES = (
    "DRAFT",
    "IN_REVIEW",
    "ACTION_REQUIRED",
    "APPROVED",
    "REJECTED",
    "COMPLETED",
)

CASE_TYPES = (
    "STATUTORY",
    "NEGOTIATED",
    "OTHER",
)


class AcquisitionCase(Base):
    """Central workflow container for a land acquisition process."""

    __tablename__ = "acquisition_cases"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    land_requirement_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "land_requirements.id",
        ),
        nullable=False,
    )

    case_number: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
    )

    case_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="STATUTORY",
        server_default="STATUTORY",
    )

    legal_route: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

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

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="DRAFT",
        server_default="DRAFT",
    )

    current_stage: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default="PROPOSAL",
        server_default="PROPOSAL",
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    opened_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

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

    __table_args__ = (
        UniqueConstraint(
            "case_number",
            name="uq_acquisition_cases_case_number",
        ),
        CheckConstraint(
            "case_type IN ("
            "'STATUTORY', "
            "'NEGOTIATED', "
            "'OTHER'"
            ")",
            name="ck_acquisition_cases_case_type",
        ),
        CheckConstraint(
            "status IN ("
            "'DRAFT', "
            "'IN_REVIEW', "
            "'ACTION_REQUIRED', "
            "'APPROVED', "
            "'REJECTED', "
            "'COMPLETED'"
            ")",
            name="ck_acquisition_cases_status",
        ),
        CheckConstraint(
            "current_stage IN ("
            "'PROPOSAL', "
            "'SCRUTINY', "
            "'SIA', "
            "'NOTIFICATION', "
            "'SURVEY', "
            "'OBJECTIONS', "
            "'DECLARATION', "
            "'CLAIMS_VERIFICATION', "
            "'VALUATION', "
            "'AWARD', "
            "'COMPENSATION', "
            "'R_AND_R', "
            "'POSSESSION', "
            "'HANDOVER', "
            "'DISPUTE', "
            "'CLOSURE'"
            ")",
            name="ck_acquisition_cases_current_stage",
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
    )


class AcquisitionCaseStageHistory(Base):
    """Immutable history of acquisition case stage transitions."""

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
        String(40),
        nullable=True,
    )

    to_stage: Mapped[str] = mapped_column(
        String(40),
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
            "to_stage IN ("
            "'PROPOSAL', "
            "'SCRUTINY', "
            "'SIA', "
            "'NOTIFICATION', "
            "'SURVEY', "
            "'OBJECTIONS', "
            "'DECLARATION', "
            "'CLAIMS_VERIFICATION', "
            "'VALUATION', "
            "'AWARD', "
            "'COMPENSATION', "
            "'R_AND_R', "
            "'POSSESSION', "
            "'HANDOVER', "
            "'DISPUTE', "
            "'CLOSURE'"
            ")",
            name="ck_case_stage_history_to_stage",
        ),
        CheckConstraint(
            "from_stage IS NULL OR from_stage IN ("
            "'PROPOSAL', "
            "'SCRUTINY', "
            "'SIA', "
            "'NOTIFICATION', "
            "'SURVEY', "
            "'OBJECTIONS', "
            "'DECLARATION', "
            "'CLAIMS_VERIFICATION', "
            "'VALUATION', "
            "'AWARD', "
            "'COMPENSATION', "
            "'R_AND_R', "
            "'POSSESSION', "
            "'HANDOVER', "
            "'DISPUTE', "
            "'CLOSURE'"
            ")",
            name="ck_case_stage_history_from_stage",
        ),
        Index(
            "ix_case_stage_history_case_id_changed_at",
            "acquisition_case_id",
            "changed_at",
        ),
    )
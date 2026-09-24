from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class LandRequirement(Base):
    """Land requirement proposed for an existing AAKAR project."""

    __tablename__ = "land_requirements"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "projects.id",
        ),
        nullable=False,
    )

    requirement_reference: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
    )

    purpose: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    required_area_sq_m: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
    )

    state: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    district: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    taluka: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    village: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="DRAFT",
        server_default="DRAFT",
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

    acquisition_cases: Mapped[list["AcquisitionCase"]] = relationship(
        back_populates="land_requirement",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "requirement_reference",
            name="uq_land_requirements_project_reference",
        ),
        CheckConstraint(
            "required_area_sq_m > 0",
            name="ck_land_requirements_required_area_positive",
        ),
        CheckConstraint(
            "status IN ("
            "'DRAFT', "
            "'SUBMITTED', "
            "'UNDER_REVIEW', "
            "'APPROVED', "
            "'REJECTED', "
            "'WITHDRAWN'"
            ")",
            name="ck_land_requirements_status",
        ),
        Index(
            "ix_land_requirements_project_id",
            "project_id",
        ),
        Index(
            "ix_land_requirements_status",
            "status",
        ),
    )
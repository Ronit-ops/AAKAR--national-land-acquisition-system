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


class CaseParcel(Base):
    """Association between an acquisition case and a parcel."""

    __tablename__ = "case_parcels"

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

    parcel_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "parcels.id",
        ),
        nullable=False,
    )

    proposed_area_sq_m: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 4),
        nullable=True,
    )

    inclusion_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="ACTIVE",
        server_default="ACTIVE",
    )

    inclusion_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    removed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    removal_reason: Mapped[str | None] = mapped_column(
        Text,
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

    acquisition_case: Mapped["AcquisitionCase"] = relationship(
        back_populates="case_parcels",
    )

    parcel: Mapped["Parcel"] = relationship(
        back_populates="case_links",
    )

    __table_args__ = (
        UniqueConstraint(
            "acquisition_case_id",
            "parcel_id",
            name="uq_case_parcels_case_parcel",
        ),
        CheckConstraint(
            "proposed_area_sq_m IS NULL OR proposed_area_sq_m > 0",
            name="ck_case_parcels_proposed_area_positive",
        ),
        CheckConstraint(
            "inclusion_status IN ('ACTIVE', 'REMOVED')",
            name="ck_case_parcels_inclusion_status",
        ),
        Index(
            "ix_case_parcels_case_id",
            "acquisition_case_id",
        ),
        Index(
            "ix_case_parcels_parcel_id",
            "parcel_id",
        ),
    )
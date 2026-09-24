from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
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


class ParcelInterest(Base):
    """Recorded interest of a right holder in a parcel."""

    __tablename__ = "parcel_interests"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    parcel_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "parcels.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    right_holder_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "right_holders.id",
        ),
        nullable=False,
    )

    interest_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    share_percentage: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 5),
        nullable=True,
    )

    verification_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="UNVERIFIED",
        server_default="UNVERIFIED",
    )

    record_source: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    record_reference: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    effective_from: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    effective_to: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(
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

    parcel: Mapped["Parcel"] = relationship(
        back_populates="interests",
    )

    right_holder: Mapped["RightHolder"] = relationship(
        back_populates="parcel_interests",
    )

    __table_args__ = (
        UniqueConstraint(
            "parcel_id",
            "right_holder_id",
            "interest_type",
            name="uq_parcel_interests_holder_type",
        ),
        CheckConstraint(
            "interest_type IN ("
            "'OWNER', "
            "'CO_OWNER', "
            "'TENANT', "
            "'OCCUPIER', "
            "'LESSEE', "
            "'OTHER'"
            ")",
            name="ck_parcel_interests_interest_type",
        ),
        CheckConstraint(
            "verification_status IN ("
            "'UNVERIFIED', "
            "'VERIFIED', "
            "'DISPUTED'"
            ")",
            name="ck_parcel_interests_verification_status",
        ),
        CheckConstraint(
            "share_percentage IS NULL "
            "OR (share_percentage >= 0 AND share_percentage <= 100)",
            name="ck_parcel_interests_share_percentage",
        ),
        CheckConstraint(
            "effective_to IS NULL "
            "OR effective_from IS NULL "
            "OR effective_to >= effective_from",
            name="ck_parcel_interests_effective_dates",
        ),
        Index(
            "ix_parcel_interests_parcel_id",
            "parcel_id",
        ),
        Index(
            "ix_parcel_interests_right_holder_id",
            "right_holder_id",
        ),
    )
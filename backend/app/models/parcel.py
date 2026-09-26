from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from geoalchemy2 import Geometry
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Parcel(Base):
    """Canonical land parcel record."""

    __tablename__ = "parcels"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    parcel_reference: Mapped[str] = mapped_column(
        String(100),
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

    survey_number: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    subdivision_number: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    recorded_area_sq_m: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
    )

    surveyed_area_sq_m: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 4),
        nullable=True,
    )

    acquired_area_sq_m: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 4),
        nullable=True,
    )

    land_category: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    land_record_reference: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    source_system: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    geometry: Mapped[object | None] = mapped_column(
        Geometry(
            geometry_type="MULTIPOLYGON",
            srid=4326,
            spatial_index=False,
        ),
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

    case_links: Mapped[list["CaseParcel"]] = relationship(
        back_populates="parcel",
        cascade="all, delete-orphan",
    )

    interests: Mapped[list["ParcelInterest"]] = relationship(
        back_populates="parcel",
        cascade="all, delete-orphan",
    )

    land_record_retrievals: Mapped[
        list["LandRecordRetrieval"]
    ] = relationship(
        back_populates="parcel",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint(
            "parcel_reference",
            name="uq_parcels_parcel_reference",
        ),
        CheckConstraint(
            "recorded_area_sq_m > 0",
            name="ck_parcels_recorded_area_positive",
        ),
        CheckConstraint(
            "surveyed_area_sq_m IS NULL OR surveyed_area_sq_m > 0",
            name="ck_parcels_surveyed_area_positive",
        ),
        CheckConstraint(
            "acquired_area_sq_m IS NULL OR acquired_area_sq_m > 0",
            name="ck_parcels_acquired_area_positive",
        ),
        Index(
            "ix_parcels_location",
            "state",
            "district",
            "taluka",
            "village",
        ),
        Index(
            "ix_parcels_survey_number",
            "survey_number",
        ),
    )
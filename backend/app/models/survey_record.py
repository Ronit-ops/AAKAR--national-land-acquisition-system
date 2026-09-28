from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from geoalchemy2 import Geometry
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


SURVEY_TYPES = (
    "PRELIMINARY",
    "JOINT_MEASUREMENT",
    "BOUNDARY_VERIFICATION",
    "RE_MEASUREMENT",
    "OTHER",
)

SURVEY_METHODS = (
    "FIELD_SURVEY",
    "GNSS",
    "TOTAL_STATION",
    "GPS",
    "DIGITIZED",
    "OTHER",
)

SURVEY_STATUSES = (
    "PLANNED",
    "IN_PROGRESS",
    "COMPLETED",
    "REQUIRES_REVIEW",
    "VERIFIED",
    "CANCELLED",
)


class SurveyRecord(Base):
    """Historical survey and measurement record for an acquisition parcel."""

    __tablename__ = "survey_records"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    acquisition_case_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "acquisition_cases.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    parcel_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "parcels.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    survey_reference: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    survey_type: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )

    survey_method: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="PLANNED",
        server_default="PLANNED",
    )

    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    conducted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    surveyor_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )

    verified_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )

    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    recorded_area_sq_m: Mapped[Decimal] = mapped_column(
        Numeric(18, 4),
        nullable=False,
    )

    measured_area_sq_m: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 4),
        nullable=True,
    )

    area_difference_sq_m: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 4),
        nullable=True,
    )

    area_difference_percentage: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 6),
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

    acquisition_case: Mapped["AcquisitionCase"] = relationship(
        back_populates="survey_records",
    )

    parcel: Mapped["Parcel"] = relationship(
        back_populates="survey_records",
    )

    surveyor: Mapped["User | None"] = relationship(
        foreign_keys=[surveyor_user_id],
    )

    verified_by: Mapped["User | None"] = relationship(
        foreign_keys=[verified_by_user_id],
    )

    __table_args__ = (
        UniqueConstraint(
            "acquisition_case_id",
            "survey_reference",
            name="uq_survey_records_case_reference",
        ),
        CheckConstraint(
            "survey_type IN "
            "('PRELIMINARY','JOINT_MEASUREMENT','BOUNDARY_VERIFICATION',"
            "'RE_MEASUREMENT','OTHER')",
            name="ck_survey_records_survey_type",
        ),
        CheckConstraint(
            "survey_method IN "
            "('FIELD_SURVEY','GNSS','TOTAL_STATION','GPS','DIGITIZED','OTHER')",
            name="ck_survey_records_survey_method",
        ),
        CheckConstraint(
            "status IN "
            "('PLANNED','IN_PROGRESS','COMPLETED','REQUIRES_REVIEW',"
            "'VERIFIED','CANCELLED')",
            name="ck_survey_records_status",
        ),
        CheckConstraint(
            "recorded_area_sq_m > 0",
            name="ck_survey_records_recorded_area_positive",
        ),
        CheckConstraint(
            "measured_area_sq_m IS NULL OR measured_area_sq_m > 0",
            name="ck_survey_records_measured_area_positive",
        ),
        CheckConstraint(
            "area_difference_sq_m IS NULL OR "
            "area_difference_sq_m = measured_area_sq_m - recorded_area_sq_m",
            name="ck_survey_records_area_difference",
        ),
        CheckConstraint(
            "area_difference_percentage IS NULL OR "
            "area_difference_percentage = "
            "((measured_area_sq_m - recorded_area_sq_m) "
            "/ recorded_area_sq_m) * 100",
            name="ck_survey_records_area_difference_percentage",
        ),
        CheckConstraint(
            "(status NOT IN "
            "('COMPLETED','REQUIRES_REVIEW','VERIFIED')) "
            "OR conducted_at IS NOT NULL",
            name="ck_survey_records_completed_requires_conducted_at",
        ),
        CheckConstraint(
            "(status != 'VERIFIED') "
            "OR (verified_by_user_id IS NOT NULL AND verified_at IS NOT NULL)",
            name="ck_survey_records_verified_requires_verifier",
        ),
        CheckConstraint(
            "verified_at IS NULL "
            "OR conducted_at IS NULL "
            "OR verified_at >= conducted_at",
            name="ck_survey_records_verified_after_conducted",
        ),
        Index(
            "ix_survey_records_case_id",
            "acquisition_case_id",
        ),
        Index(
            "ix_survey_records_parcel_id",
            "parcel_id",
        ),
        Index(
            "ix_survey_records_status",
            "status",
        ),
        Index(
            "ix_survey_records_conducted_at",
            "conducted_at",
        ),
    )
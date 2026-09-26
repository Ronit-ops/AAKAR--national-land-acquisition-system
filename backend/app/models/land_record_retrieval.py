from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class LandRecordRetrieval(Base):
    """Provenance record for a land-record retrieval attempt."""

    __tablename__ = "land_record_retrievals"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    parcel_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "parcels.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    provider: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    source_system: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    source_record_reference: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    retrieved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    source_version: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    error_code: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    error_message: Mapped[str | None] = mapped_column(
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
        back_populates="land_record_retrievals",
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ("
            "'REQUESTED', "
            "'SUCCESS', "
            "'NO_RECORD', "
            "'FAILED'"
            ")",
            name="ck_land_record_retrievals_status",
        ),
        CheckConstraint(
            "retrieved_at IS NULL "
            "OR retrieved_at >= requested_at",
            name="ck_land_record_retrievals_retrieved_after_requested",
        ),
        Index(
            "ix_land_record_retrievals_parcel_id",
            "parcel_id",
        ),
        Index(
            "ix_land_record_retrievals_source_record_reference",
            "source_record_reference",
        ),
        Index(
            "ix_land_record_retrievals_status",
            "status",
        ),
        Index(
            "ix_land_record_retrievals_requested_at",
            "requested_at",
        ),
    )
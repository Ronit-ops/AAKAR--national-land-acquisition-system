from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RightHolder(Base):
    """Person or entity recorded as holding an interest in land."""

    __tablename__ = "right_holders"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    holder_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    display_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    external_reference: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    contact_email: Mapped[str | None] = mapped_column(
        String(320),
        nullable=True,
    )

    contact_phone: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
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

    parcel_interests: Mapped[list["ParcelInterest"]] = relationship(
        back_populates="right_holder",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "holder_type IN ("
            "'INDIVIDUAL', "
            "'ENTITY', "
            "'GOVERNMENT', "
            "'COMMUNITY', "
            "'OTHER'"
            ")",
            name="ck_right_holders_holder_type",
        ),
        Index(
            "ix_right_holders_display_name",
            "display_name",
        ),
        Index(
            "ix_right_holders_external_reference",
            "external_reference",
        ),
    )
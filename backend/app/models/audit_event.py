from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuditEvent(Base):
    """Persistent audit event for important AAKAR platform actions."""

    __tablename__ = "audit_events"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    actor_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    action: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
        index=True,
    )

    entity_type: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
    )

    entity_id: Mapped[UUID | None] = mapped_column(
        nullable=True,
        index=True,
    )

    result: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="success",
        server_default="success",
    )

    details: Mapped[dict[str, object] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    __table_args__ = (
        Index(
            "ix_audit_events_entity",
            "entity_type",
            "entity_id",
        ),
    )

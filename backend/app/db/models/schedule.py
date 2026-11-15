import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Text,
    Uuid,
    false,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, created_at, updated_at, uuid_pk
from app.db.enums import ScheduleKind, pg_enum


class ScheduleItem(Base):
    __tablename__ = "schedule_items"
    __table_args__ = (
        CheckConstraint("starts_at IS NOT NULL OR due_at IS NOT NULL", name="has_date"),
        Index("idx_schedule_bot_due", "bot_id", "due_at"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    bot_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("bots.id", ondelete="CASCADE"), nullable=False
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("documents.id", ondelete="CASCADE")
    )  # NULL if added manually
    title: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[ScheduleKind] = mapped_column(
        pg_enum(ScheduleKind, "schedule_kind"),
        nullable=False,
        server_default=ScheduleKind.OTHER.value,
    )
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    all_day: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=true())
    location: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    source_chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("chunks.id", ondelete="SET NULL")
    )
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false())
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = updated_at()

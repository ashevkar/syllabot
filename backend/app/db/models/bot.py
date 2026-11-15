import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Text, Uuid, false, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, created_at, updated_at, uuid_pk
from app.db.enums import BotStatus, CollabLevel, pg_enum


class Bot(Base):
    """A course bot.

    Template values are copied in at creation; `template_id` only records origin (FR-8).
    """

    __tablename__ = "bots"
    __table_args__ = (Index("idx_bots_owner", "owner_id"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("templates.id", ondelete="SET NULL")
    )
    course_name: Mapped[str] = mapped_column(Text, nullable=False)
    course_code: Mapped[str | None] = mapped_column(Text)
    term: Mapped[str | None] = mapped_column(Text)  # 'Fall 2026'
    timezone: Mapped[str] = mapped_column(Text, nullable=False, server_default="America/Phoenix")
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    settings: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'")
    )  # {"top_k": 6, "min_score": 0.35, ...}
    welcome_message: Mapped[str | None] = mapped_column(Text)
    suggested_questions: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("'{}'")
    )
    fallback_message: Mapped[str] = mapped_column(Text, nullable=False)
    contact_info: Mapped[str | None] = mapped_column(Text)  # shown in fallback replies
    status: Mapped[BotStatus] = mapped_column(
        pg_enum(BotStatus, "bot_status"), nullable=False, server_default=BotStatus.DRAFT.value
    )
    share_slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    require_login: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false())
    rate_limit_per_min: Mapped[int] = mapped_column(Integer, nullable=False, server_default="20")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created_at()
    updated_at: Mapped[datetime] = updated_at()


class BotCollaborator(Base):
    __tablename__ = "bot_collaborators"
    __table_args__ = (Index("idx_collab_user", "user_id"),)

    bot_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("bots.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    level: Mapped[CollabLevel] = mapped_column(
        pg_enum(CollabLevel, "collab_level"),
        nullable=False,
        server_default=CollabLevel.EDITOR.value,
    )
    added_at: Mapped[datetime] = created_at()

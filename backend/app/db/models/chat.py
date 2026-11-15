import uuid
from datetime import datetime

from sqlalchemy import (
    REAL,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    Text,
    Uuid,
    false,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, created_at, uuid_pk
from app.db.enums import MessageRole, pg_enum


class ChatSession(Base):
    """An anonymous student (or instructor preview) conversation with one bot."""

    __tablename__ = "chat_sessions"
    __table_args__ = (Index("idx_sessions_bot_time", "bot_id", "started_at"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    bot_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("bots.id", ondelete="CASCADE"), nullable=False
    )
    is_preview: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false())
    client_hash: Mapped[str | None] = mapped_column(Text)  # HMAC of IP + user agent, no raw PII
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ChatMessage(Base):
    """One turn. `bot_id` is duplicated from the session for fast analytics queries."""

    __tablename__ = "chat_messages"
    __table_args__ = (
        CheckConstraint("feedback IN (-1, 1)", name="feedback_vote"),
        Index("idx_messages_session", "session_id", "created_at"),
        Index("idx_messages_bot_time", "bot_id", "created_at"),
        Index("idx_messages_bot_fallback", "bot_id", postgresql_where="is_fallback"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False
    )
    bot_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("bots.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[MessageRole] = mapped_column(pg_enum(MessageRole, "message_role"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Assistant-only fields
    retrieved_chunk_ids: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(Uuid))
    top_score: Mapped[float | None] = mapped_column(REAL)
    used_schedule: Mapped[bool | None] = mapped_column(Boolean)
    is_fallback: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false())
    model: Mapped[str | None] = mapped_column(Text)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    completion_tokens: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    feedback: Mapped[int | None] = mapped_column(SmallInteger)  # -1 thumbs down, 1 thumbs up
    created_at: Mapped[datetime] = created_at()

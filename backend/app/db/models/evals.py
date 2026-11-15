import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    Uuid,
    false,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, created_at, uuid_pk
from app.db.enums import EvalVerdict, RunStatus, pg_enum


class EvalCase(Base):
    __tablename__ = "eval_cases"
    __table_args__ = (Index("idx_eval_cases_bot", "bot_id"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    bot_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("bots.id", ondelete="CASCADE"), nullable=False
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    expected_answer: Mapped[str] = mapped_column(Text, nullable=False)
    expect_fallback: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=false())
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = created_at()


class EvalRun(Base):
    __tablename__ = "eval_runs"
    __table_args__ = (Index("idx_eval_runs_bot", "bot_id", text("created_at DESC")),)

    id: Mapped[uuid.UUID] = uuid_pk()
    bot_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("bots.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[RunStatus] = mapped_column(
        pg_enum(RunStatus, "run_status"), nullable=False, server_default=RunStatus.QUEUED.value
    )
    model: Mapped[str] = mapped_column(Text, nullable=False)
    total: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    passed: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    partial: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    failed: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    triggered_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created_at()


class EvalResult(Base):
    __tablename__ = "eval_results"
    __table_args__ = (UniqueConstraint("run_id", "case_id"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("eval_runs.id", ondelete="CASCADE"), nullable=False
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("eval_cases.id", ondelete="CASCADE"), nullable=False
    )
    actual_answer: Mapped[str | None] = mapped_column(Text)
    verdict: Mapped[EvalVerdict] = mapped_column(
        pg_enum(EvalVerdict, "eval_verdict"), nullable=False
    )
    judge_reason: Mapped[str | None] = mapped_column(Text)
    retrieved_chunk_ids: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(Uuid))
    latency_ms: Mapped[int | None] = mapped_column(Integer)

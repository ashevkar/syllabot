import uuid
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, Integer, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, created_at, uuid_pk
from app.db.enums import DocSource, DocStatus, pg_enum


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint(
            "(source_type = 'file' AND storage_key IS NOT NULL) OR "
            "(source_type = 'url' AND source_url IS NOT NULL)",
            name="source_location",
        ),
        Index("idx_documents_bot", "bot_id"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    bot_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("bots.id", ondelete="CASCADE"), nullable=False
    )
    source_type: Mapped[DocSource] = mapped_column(
        pg_enum(DocSource, "doc_source"), nullable=False, server_default=DocSource.FILE.value
    )
    filename: Mapped[str | None] = mapped_column(Text)  # original name (file sources)
    source_url: Mapped[str | None] = mapped_column(Text)  # url sources
    storage_key: Mapped[str | None] = mapped_column(Text)  # random path / S3 key
    mime_type: Mapped[str | None] = mapped_column(Text)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    content_hash: Mapped[str | None] = mapped_column(Text)  # sha256
    status: Mapped[DocStatus] = mapped_column(
        pg_enum(DocStatus, "doc_status"), nullable=False, server_default=DocStatus.UPLOADED.value
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    page_count: Mapped[int | None] = mapped_column(Integer)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = created_at()
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

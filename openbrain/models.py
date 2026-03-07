import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from openbrain.db import Base
from openbrain.config import settings


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MemoryRecord(Base):
    __tablename__ = "memory_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    cleaned_text: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    memory_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_surface: Mapped[str] = mapped_column(String(64), nullable=False)
    source_session_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    project: Mapped[str | None] = mapped_column(Text, nullable=True)

    people: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    topics: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    tags: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    action_items: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    importance: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    sensitivity: Mapped[str] = mapped_column(String(32), default="normal", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)

    provenance_type: Mapped[str] = mapped_column(String(32), default="local", nullable=False)
    provenance_ref: Mapped[str | None] = mapped_column(Text, nullable=True)

    archive_path: Mapped[str] = mapped_column(Text, nullable=False)

    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    embedding: Mapped[list[float] | None] = mapped_column(Vector(settings.embed_dim), nullable=True)


class ExternalPromotion(Base):
    __tablename__ = "external_promotions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    local_memory_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    external_source: Mapped[str] = mapped_column(Text, nullable=False)
    external_title: Mapped[str] = mapped_column(Text, nullable=False)
    external_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    promotion_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class GatewayAuditLog(Base):
    __tablename__ = "gateway_audit_log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


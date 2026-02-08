from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class SourceFile(Base):
    __tablename__ = "source_file"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sha256: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    size: Mapped[int] = mapped_column(Integer)
    uri: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class UploadSession(Base):
    __tablename__ = "upload_session"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename: Mapped[str] = mapped_column(String(255))
    size: Mapped[int] = mapped_column(Integer)
    temp_path: Mapped[str] = mapped_column(String(500))
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class IngestJob(Base):
    __tablename__ = "ingest_job"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_file_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("source_file.id"))
    status: Mapped[str] = mapped_column(String(40), default="queued")
    progress_json: Mapped[dict | None] = mapped_column(JSON, default=dict)
    stats_json: Mapped[dict | None] = mapped_column(JSON, default=dict)
    error_text: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class RawBlock(Base):
    __tablename__ = "raw_block"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_file_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("source_file.id"))
    uri: Mapped[str] = mapped_column(String(500))
    codec: Mapped[str] = mapped_column(String(20), default="zstd")
    line_count: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class DictEventType(Base):
    __tablename__ = "dict_event_type"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(100), unique=True)


class DictItem(Base):
    __tablename__ = "dict_item"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)


class DictContainer(Base):
    __tablename__ = "dict_container"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(200), unique=True)
    owner_player_id: Mapped[str | None] = mapped_column(String(50))


class DictPlayer(Base):
    __tablename__ = "dict_player"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_id: Mapped[str] = mapped_column(String(50), unique=True)


class DictAlias(Base):
    __tablename__ = "dict_alias"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(Integer, ForeignKey("dict_player.id"))
    alias: Mapped[str] = mapped_column(String(200))


class Event(Base):
    __tablename__ = "event"
    __table_args__ = (
        UniqueConstraint("dedupe_hash", name="uq_event_dedupe"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_file_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("source_file.id"))
    parser_id: Mapped[str] = mapped_column(String(50))
    parser_version: Mapped[str] = mapped_column(String(20))
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    occurred_at_quality: Mapped[str] = mapped_column(String(20))
    event_type_id: Mapped[int] = mapped_column(Integer, ForeignKey("dict_event_type.id"))
    src_player_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("dict_player.id"))
    dst_player_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("dict_player.id"))
    item_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("dict_item.id"))
    container_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("dict_container.id"))
    amount: Mapped[Numeric | None] = mapped_column(Numeric(20, 2))
    qty: Mapped[Numeric | None] = mapped_column(Numeric(20, 2))
    metadata: Mapped[dict | None] = mapped_column(JSON, default=dict)
    raw_block_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("raw_block.id"))
    raw_line_index: Mapped[int] = mapped_column(Integer)
    dedupe_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class UnknownSignature(Base):
    __tablename__ = "unknown_signature"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ingest_job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ingest_job.id"))
    signature: Mapped[str] = mapped_column(String(400))
    count: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

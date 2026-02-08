from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class UploadCreate(BaseModel):
    filename: str
    size: int
    chunk_size: int = 1024 * 1024
    expected_chunks: int | None = None


class UploadSessionOut(BaseModel):
    id: UUID
    filename: str
    size: int
    status: str
    chunk_size: int
    expected_chunks: int | None
    received_chunks: list[int]


class SourceFileOut(BaseModel):
    id: UUID
    sha256: str
    name: str
    size: int
    uri: str
    created_at: datetime


class IngestJobCreate(BaseModel):
    source_file_id: UUID


class IngestJobOut(BaseModel):
    id: int
    source_file_id: UUID
    status: str
    progress_json: dict | None
    stats_json: dict | None
    error_text: Optional[str]
    created_at: datetime
    updated_at: datetime


class EventOut(BaseModel):
    id: UUID
    ingest_job_id: int
    occurred_at: Optional[datetime]
    occurred_at_quality: str
    event_type: str
    src_player_id: Optional[str]
    dst_player_id: Optional[str]
    item: Optional[str]
    container: Optional[str]
    money: Optional[int]
    qty: Optional[int]
    metadata: dict | None
    raw_block_id: UUID
    raw_line_index: int
    global_line_no: int


class EvidenceOut(BaseModel):
    raw_block_id: UUID
    line_index: int
    line: str
    context_before: list[str]
    context_after: list[str]
    global_line_no: int | None = None


class ReportPackCreate(BaseModel):
    name: str = Field(default="report-pack")
    filters: dict = Field(default_factory=dict)


class ReportPackOut(BaseModel):
    id: UUID
    name: str
    filter_json: dict
    uri: str
    created_at: datetime

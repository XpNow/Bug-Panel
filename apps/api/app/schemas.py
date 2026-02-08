from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class UploadCreate(BaseModel):
    filename: str
    size: int


class UploadSessionOut(BaseModel):
    id: UUID
    filename: str
    size: int
    completed: bool


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
    id: UUID
    source_file_id: UUID
    status: str
    progress_json: dict | None
    stats_json: dict | None
    error_text: Optional[str]
    created_at: datetime
    updated_at: datetime


class EventOut(BaseModel):
    id: UUID
    occurred_at: Optional[datetime]
    occurred_at_quality: str
    event_type: str
    src_player_id: Optional[str]
    dst_player_id: Optional[str]
    item: Optional[str]
    container: Optional[str]
    amount: Optional[float]
    qty: Optional[float]
    metadata: dict | None
    raw_block_id: UUID
    raw_line_index: int


class EvidenceOut(BaseModel):
    raw_block_id: UUID
    line_index: int
    context: list[str]


class ReportPackCreate(BaseModel):
    name: str = Field(default="report-pack")
    filters: dict = Field(default_factory=dict)


class ReportPackOut(BaseModel):
    id: UUID
    name: str
    filter_json: dict
    uri: str
    created_at: datetime

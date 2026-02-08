from __future__ import annotations

import hashlib
import re
import uuid
from collections import Counter
from datetime import datetime
from pathlib import Path

import zstandard as zstd
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .models import (
    DictContainer,
    DictEventType,
    DictItem,
    DictPlayer,
    Event,
    IngestJob,
    RawBlock,
    SourceFile,
    UnknownSignature,
)
from .normalizer import TIMEZONE, normalize_lines
from .object_store import object_store
from .parsers import PARSERS, EventData, NormalizedBlock


class RawBlockWriter:
    def __init__(self, db: Session, source_file_id: uuid.UUID, block_size: int = 500) -> None:
        self.db = db
        self.source_file_id = source_file_id
        self.block_size = block_size
        self.lines: list[str] = []
        self.block_id = uuid.uuid4()

    def append(self, line: str) -> tuple[str, int]:
        raw_block_id = str(self.block_id)
        index = len(self.lines)
        self.lines.append(line)
        if len(self.lines) >= self.block_size:
            self.flush()
        return raw_block_id, index

    def flush(self) -> None:
        if not self.lines:
            return
        path = object_store.raw_block_path(self.source_file_id, self.block_id)
        compressor = zstd.ZstdCompressor(level=10)
        data = "\n".join(self.lines).encode("utf-8")
        with path.open("wb") as handle:
            handle.write(compressor.compress(data))
        raw_block = RawBlock(
            id=self.block_id,
            source_file_id=self.source_file_id,
            uri=str(path),
            codec="zstd",
            line_count=len(self.lines),
            created_at=datetime.utcnow(),
        )
        self.db.add(raw_block)
        self.db.commit()
        self.lines = []
        self.block_id = uuid.uuid4()


class IngestRunner:
    def __init__(self, db: Session) -> None:
        self.db = db

    def run_next_job(self) -> bool:
        job = (
            self.db.query(IngestJob)
            .filter(IngestJob.status == "queued")
            .order_by(IngestJob.created_at)
            .first()
        )
        if not job:
            return False
        job.status = "running"
        job.updated_at = datetime.utcnow()
        self.db.commit()
        try:
            self._process_job(job)
            job.status = "completed"
            job.updated_at = datetime.utcnow()
            self.db.commit()
        except Exception as exc:  # noqa: BLE001
            job.status = "failed"
            job.error_text = str(exc)
            job.updated_at = datetime.utcnow()
            self.db.commit()
        return True

    def _process_job(self, job: IngestJob) -> None:
        source_file = self.db.get(SourceFile, job.source_file_id)
        if not source_file:
            raise ValueError("Source file missing")
        writer = RawBlockWriter(self.db, source_file.id)
        unknown_signatures: Counter[str] = Counter()
        job_date = datetime.now(TIMEZONE)

        def line_iterator():
            with Path(source_file.uri).open("r", encoding="utf-8", errors="replace") as handle:
                for raw_line in handle:
                    raw_line = raw_line.rstrip("\n")
                    raw_block_id, raw_line_index = writer.append(raw_line)
                    yield raw_line, raw_block_id, raw_line_index
            writer.flush()

        for block in normalize_lines(line_iterator(), job_date):
            parsed_any = False
            for parser in PARSERS:
                if parser.match(block):
                    for event in parser.parse(block):
                        self._store_event(job, source_file, block, event, parser)
                        parsed_any = True
            if not parsed_any:
                for payload in block.payload:
                    signature = normalize_signature(payload.text)
                    unknown_signatures[signature] += 1

        if unknown_signatures:
            for signature, count in unknown_signatures.most_common(50):
                self.db.add(
                    UnknownSignature(
                        ingest_job_id=job.id,
                        signature=signature,
                        count=count,
                    )
                )
            job.stats_json = {"unknown_signatures": unknown_signatures.most_common(50)}
            self.db.commit()

    def _store_event(
        self,
        job: IngestJob,
        source_file: SourceFile,
        block: NormalizedBlock,
        event: EventData,
        parser,
    ) -> None:
        event_type_id = self._get_or_create_event_type(event.event_type)
        src_id = self._get_or_create_player(event.src_player_id) if event.src_player_id else None
        dst_id = self._get_or_create_player(event.dst_player_id) if event.dst_player_id else None
        item_id = self._get_or_create_item(event.item) if event.item else None
        container_id = self._get_or_create_container(event.container) if event.container else None

        dedupe_seed = (
            f"{source_file.sha256}:{event.raw_block_id}:{event.raw_line_index}:{event.event_type}"
        )
        dedupe_hash = hashlib.sha256(dedupe_seed.encode("utf-8")).hexdigest()
        self._ensure_partition(block.occurred_at)
        db_event = Event(
            source_file_id=source_file.id,
            parser_id=parser.parser_id,
            parser_version=parser.version,
            occurred_at=block.occurred_at,
            occurred_at_quality=block.occurred_at_quality,
            event_type_id=event_type_id,
            src_player_id=src_id,
            dst_player_id=dst_id,
            item_id=item_id,
            container_id=container_id,
            amount=event.amount,
            qty=event.qty,
            metadata=event.metadata or {},
            raw_block_id=uuid.UUID(event.raw_block_id),
            raw_line_index=event.raw_line_index,
            dedupe_hash=dedupe_hash,
            created_at=datetime.utcnow(),
        )
        self.db.add(db_event)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()

    def _get_or_create_event_type(self, key: str) -> int:
        row = self.db.query(DictEventType).filter(DictEventType.key == key).one_or_none()
        if row:
            return row.id
        row = DictEventType(key=key)
        self.db.add(row)
        self.db.commit()
        return row.id

    def _get_or_create_item(self, name: str) -> int:
        row = self.db.query(DictItem).filter(DictItem.name == name).one_or_none()
        if row:
            return row.id
        row = DictItem(name=name)
        self.db.add(row)
        self.db.commit()
        return row.id

    def _get_or_create_container(self, key: str) -> int:
        row = self.db.query(DictContainer).filter(DictContainer.key == key).one_or_none()
        if row:
            return row.id
        owner = None
        if key.startswith("portbagaj_"):
            parts = key.split("_")
            if len(parts) > 1:
                owner = parts[1]
        row = DictContainer(key=key, owner_player_id=owner)
        self.db.add(row)
        self.db.commit()
        return row.id

    def _get_or_create_player(self, player_id: str) -> int:
        row = self.db.query(DictPlayer).filter(DictPlayer.player_id == player_id).one_or_none()
        if row:
            return row.id
        row = DictPlayer(player_id=player_id)
        self.db.add(row)
        self.db.commit()
        return row.id

    def _ensure_partition(self, occurred_at: datetime | None) -> None:
        if not occurred_at:
            return
        month_start = datetime(occurred_at.year, occurred_at.month, 1)
        if occurred_at.month == 12:
            month_end = datetime(occurred_at.year + 1, 1, 1)
        else:
            month_end = datetime(occurred_at.year, occurred_at.month + 1, 1)
        partition_name = f"event_{month_start:%Y_%m}"
        self.db.execute(
            text(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_class WHERE relname = :partition_name
                    ) THEN
                        EXECUTE format(
                            'CREATE TABLE %I PARTITION OF event FOR VALUES FROM (%L) TO (%L)',
                            :partition_name,
                            :start,
                            :end
                        );
                    END IF;
                END $$;
                """
            ),
            {
                "partition_name": partition_name,
                "start": month_start.isoformat(),
                "end": month_end.isoformat(),
            },
        )
        self.db.commit()


def normalize_signature(text: str) -> str:
    text = re.sub(r"\d+", "<#>", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()

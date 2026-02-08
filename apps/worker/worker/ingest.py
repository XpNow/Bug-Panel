from __future__ import annotations

import hashlib
import logging
import re
import uuid
from collections import Counter
from datetime import datetime
from pathlib import Path

import zstandard as zstd
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert
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
        self.logger = logging.getLogger("phx.worker")

    def run_next_job(self) -> bool:
        job = (
            self.db.query(IngestJob)
            .filter(IngestJob.status == "queued")
            .order_by(IngestJob.created_at)
            .first()
        )
        if not job:
            return False
        self.logger.info("Starting ingest job %s", job.id)
        job.status = "running"
        job.updated_at = datetime.utcnow()
        self.db.commit()
        try:
            self._process_job(job)
            job.status = "completed"
            job.updated_at = datetime.utcnow()
            self.db.commit()
            self.logger.info("Completed ingest job %s", job.id)
        except Exception as exc:  # noqa: BLE001
            job.status = "failed"
            job.error_text = str(exc)
            job.updated_at = datetime.utcnow()
            self.db.commit()
            self.logger.exception("Failed ingest job %s", job.id)
        return True

    def _process_job(self, job: IngestJob) -> None:
        source_file = self.db.get(SourceFile, job.source_file_id)
        if not source_file:
            raise ValueError("Source file missing")
        writer = RawBlockWriter(self.db, source_file.id)
        unknown_signatures: Counter[str] = Counter()
        event_type_counts: Counter[str] = Counter()
        parser_counts: Counter[str] = Counter()
        ts_quality_counts: Counter[str] = Counter()
        job_date = datetime.now(TIMEZONE)
        global_line_no = 0

        def line_iterator():
            nonlocal global_line_no
            with Path(source_file.uri).open("r", encoding="utf-8", errors="replace") as handle:
                for raw_line in handle:
                    raw_line = raw_line.rstrip("\n")
                    raw_block_id, raw_line_index = writer.append(raw_line)
                    global_line_no += 1
                    yield raw_line, raw_block_id, raw_line_index, global_line_no
            writer.flush()

        for block in normalize_lines(line_iterator(), job_date):
            parsed_any = False
            ts_quality_counts[block.occurred_at_quality] += 1
            for parser in PARSERS:
                if parser.match(block):
                    for event in parser.parse(block):
                        self._store_event(job, source_file, block, event, parser)
                        event_type_counts[event.event_type] += 1
                        parser_counts[parser.parser_id] += 1
                        parsed_any = True
            if not parsed_any:
                for payload in block.payload:
                    signature = normalize_signature(payload.text)
                    unknown_signatures[signature] += 1

        for signature, count in unknown_signatures.most_common(50):
            self.db.add(
                UnknownSignature(
                    ingest_job_id=job.id,
                    signature=signature,
                    count=count,
                )
            )
        job.stats_json = {
            "event_type_counts": event_type_counts.most_common(),
            "parser_counts": parser_counts.most_common(),
            "unknown_signatures": unknown_signatures.most_common(50),
            "ts_quality_counts": ts_quality_counts.most_common(),
        }
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
        if event.global_line_no is None:
            self.logger.warning("Skipping event without global line no: %s", event)
            return
        src_id = self._get_or_create_player(event.src_player_id) if event.src_player_id else None
        dst_id = self._get_or_create_player(event.dst_player_id) if event.dst_player_id else None
        item_id = self._get_or_create_item(event.item) if event.item else None
        container_id = self._get_or_create_container(event.container) if event.container else None

        dedupe_seed = (
            f"{source_file.sha256}:{event.global_line_no}:{event_type_id}:{event.event_type}"
        )
        dedupe_key = hashlib.sha256(dedupe_seed.encode("utf-8")).hexdigest()
        self._ensure_partition(block.occurred_at)
        event_values = {
            "id": uuid.uuid4(),
            "source_file_id": source_file.id,
            "ingest_job_id": job.id,
            "parser_id": parser.parser_id,
            "parser_version": parser.version,
            "occurred_at": block.occurred_at,
            "occurred_at_quality": block.occurred_at_quality,
            "event_type_id": event_type_id,
            "src_player_id": src_id,
            "dst_player_id": dst_id,
            "item_id": item_id,
            "container_id": container_id,
            "money": event.money,
            "qty": event.qty,
            "metadata": event.metadata or {},
            "raw_block_id": uuid.UUID(event.raw_block_id),
            "raw_line_index": event.raw_line_index,
            "global_line_no": event.global_line_no,
            "dedupe_key": dedupe_key,
            "created_at": datetime.utcnow(),
        }
        stmt = insert(Event).values(**event_values).on_conflict_do_nothing(
            index_elements=["dedupe_key"]
        )
        try:
            self.db.execute(stmt)
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
                        EXECUTE format(
                            'CREATE UNIQUE INDEX %I ON %I (dedupe_key)',
                            :partition_name || '_dedupe_key_uq',
                            :partition_name
                        );
                        EXECUTE format(
                            'CREATE INDEX %I ON %I (ingest_job_id, occurred_at)',
                            :partition_name || '_job_time_idx',
                            :partition_name
                        );
                        EXECUTE format(
                            'CREATE INDEX %I ON %I (ingest_job_id, event_type_id)',
                            :partition_name || '_job_type_idx',
                            :partition_name
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

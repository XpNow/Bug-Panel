from __future__ import annotations

import csv
import io
import json
import uuid
import zipfile
from datetime import datetime

import zstandard as zstd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, aliased

from ..deps import get_db
from ..models import Event, DictEventType, DictPlayer, DictItem, DictContainer, RawBlock, ReportPack
from ..schemas import ReportPackCreate, ReportPackOut
from ..storage import object_store

router = APIRouter(prefix="/report-packs", tags=["report-packs"])


def _load_raw_block_lines(db: Session, raw_block_id: uuid.UUID) -> list[str]:
    raw_block = db.get(RawBlock, raw_block_id)
    if not raw_block:
        return []
    with object_store.open_raw_block(raw_block.uri) as handle:
        decompressor = zstd.ZstdDecompressor()
        data = decompressor.stream_reader(handle).read()
    return data.decode("utf-8", errors="replace").splitlines()


@router.post("", response_model=ReportPackOut)
def create_report_pack(payload: ReportPackCreate, db: Session = Depends(get_db)):
    filters = payload.filters or {}
    event_type = filters.get("event_type")
    player_id = filters.get("player_id")
    ingest_job_id = filters.get("ingest_job_id")
    start = filters.get("start")
    end = filters.get("end")

    src_player = aliased(DictPlayer)
    dst_player = aliased(DictPlayer)
    query = (
        db.query(Event, DictEventType, src_player, dst_player, DictItem, DictContainer)
        .join(DictEventType, Event.event_type_id == DictEventType.id)
        .outerjoin(src_player, Event.src_player_id == src_player.id)
        .outerjoin(dst_player, Event.dst_player_id == dst_player.id)
        .outerjoin(DictItem, Event.item_id == DictItem.id)
        .outerjoin(DictContainer, Event.container_id == DictContainer.id)
    )
    if event_type:
        query = query.filter(DictEventType.key == event_type)
    if ingest_job_id:
        query = query.filter(Event.ingest_job_id == ingest_job_id)
    if player_id:
        query = query.filter((src_player.player_id == player_id) | (dst_player.player_id == player_id))
    if start:
        query = query.filter(Event.occurred_at >= datetime.fromisoformat(start))
    if end:
        query = query.filter(Event.occurred_at <= datetime.fromisoformat(end))

    events = query.order_by(Event.created_at.desc()).all()

    manifest = {
        "generated_at": datetime.utcnow().isoformat(),
        "filters": filters,
        "event_count": len(events),
    }

    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zip_handle:
        zip_handle.writestr("manifest.json", json.dumps(manifest, indent=2))
        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)
        writer.writerow(
            [
                "event_id",
                "occurred_at",
                "event_type",
                "src_player_id",
                "dst_player_id",
                "item",
                "container",
                "money",
                "qty",
                "ingest_job_id",
                "raw_block_id",
                "raw_line_index",
            ]
        )
        evidence_lines = []
        raw_cache: dict[uuid.UUID, list[str]] = {}
        for event, event_type_row, src, dst, item, container in events:
            writer.writerow(
                [
                    str(event.id),
                    event.occurred_at.isoformat() if event.occurred_at else "",
                    event_type_row.key,
                    src.player_id if src else "",
                    dst.player_id if dst else "",
                    item.name if item else "",
                    container.key if container else "",
                    event.money if event.money is not None else "",
                    event.qty if event.qty is not None else "",
                    event.ingest_job_id,
                    str(event.raw_block_id),
                    event.raw_line_index,
                ]
            )
            if event.raw_block_id not in raw_cache:
                raw_cache[event.raw_block_id] = _load_raw_block_lines(db, event.raw_block_id)
            lines = raw_cache[event.raw_block_id]
            if 0 <= event.raw_line_index < len(lines):
                context_start = max(0, event.raw_line_index - 2)
                context_end = min(len(lines), event.raw_line_index + 3)
                evidence_lines.append(
                    f"[{event.id}]\n" + "\n".join(lines[context_start:context_end]) + "\n"
                )
        zip_handle.writestr("events.csv", csv_buffer.getvalue())
        zip_handle.writestr("evidence.txt", "\n".join(evidence_lines))

    output.seek(0)
    pack_name = f"{payload.name}-{uuid.uuid4()}.zip"
    target_path = object_store.get_report_pack_path(pack_name)
    with target_path.open("wb") as handle:
        handle.write(output.read())

    report_pack = ReportPack(name=payload.name, filter_json=filters, uri=str(target_path))
    db.add(report_pack)
    db.commit()
    db.refresh(report_pack)

    return ReportPackOut(
        id=report_pack.id,
        name=report_pack.name,
        filter_json=report_pack.filter_json,
        uri=report_pack.uri,
        created_at=report_pack.created_at,
    )


@router.get("", response_model=list[ReportPackOut])
def list_report_packs(db: Session = Depends(get_db)):
    packs = db.query(ReportPack).order_by(ReportPack.created_at.desc()).all()
    return [
        ReportPackOut(
            id=pack.id,
            name=pack.name,
            filter_json=pack.filter_json,
            uri=pack.uri,
            created_at=pack.created_at,
        )
        for pack in packs
    ]


@router.get("/{pack_id}", response_model=ReportPackOut)
def get_report_pack(pack_id: uuid.UUID, db: Session = Depends(get_db)):
    pack = db.get(ReportPack, pack_id)
    if not pack:
        raise HTTPException(status_code=404, detail="Report pack not found")
    return ReportPackOut(
        id=pack.id,
        name=pack.name,
        filter_json=pack.filter_json,
        uri=pack.uri,
        created_at=pack.created_at,
    )


@router.get("/{pack_id}/download")
def download_report_pack(pack_id: uuid.UUID, db: Session = Depends(get_db)):
    pack = db.get(ReportPack, pack_id)
    if not pack:
        raise HTTPException(status_code=404, detail="Report pack not found")
    return {"uri": pack.uri}


@router.get("/{pack_id}/file")
def get_report_pack_file(pack_id: uuid.UUID, path: str, db: Session = Depends(get_db)):
    pack = db.get(ReportPack, pack_id)
    if not pack:
        raise HTTPException(status_code=404, detail="Report pack not found")
    return {"uri": pack.uri, "path": path}

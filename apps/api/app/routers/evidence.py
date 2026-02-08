from __future__ import annotations

import uuid

import zstandard as zstd
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..deps import get_db
from ..models import RawBlock
from ..schemas import EvidenceOut
from ..storage import object_store

router = APIRouter(prefix="/evidence", tags=["evidence"])


@router.get("/raw-line", response_model=EvidenceOut)
def get_raw_line(
    raw_block_id: uuid.UUID,
    line_index: int,
    context: int = Query(default=2, le=10),
    db: Session = Depends(get_db),
):
    raw_block = db.get(RawBlock, raw_block_id)
    if not raw_block:
        raise HTTPException(status_code=404, detail="Raw block not found")
    with object_store.open_raw_block(raw_block.uri) as handle:
        decompressor = zstd.ZstdDecompressor()
        data = decompressor.stream_reader(handle).read()
    lines = data.decode("utf-8", errors="replace").splitlines()
    if line_index < 0 or line_index >= len(lines):
        raise HTTPException(status_code=404, detail="Line index out of range")
    start = max(0, line_index - context)
    end = min(len(lines), line_index + context + 1)
    context_before = lines[start:line_index]
    context_after = lines[line_index + 1 : end]
    return EvidenceOut(
        raw_block_id=raw_block_id,
        line_index=line_index,
        line=lines[line_index],
        context_before=context_before,
        context_after=context_after,
        global_line_no=None,
    )

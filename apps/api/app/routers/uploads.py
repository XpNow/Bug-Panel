from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from ..deps import get_db
from ..models import UploadSession, SourceFile
from ..schemas import UploadCreate, UploadSessionOut, SourceFileOut
from ..storage import object_store

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("/create", response_model=UploadSessionOut)
def create_upload(payload: UploadCreate, db: Session = Depends(get_db)):
    upload_id = uuid.uuid4()
    temp_prefix = object_store.create_upload_prefix(str(upload_id))
    session = UploadSession(
        id=upload_id,
        filename=payload.filename,
        size=payload.size,
        status="OPEN",
        chunk_size=payload.chunk_size,
        expected_chunks=payload.expected_chunks,
        received_chunks=[],
        temp_prefix=str(temp_prefix),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return UploadSessionOut(
        id=session.id,
        filename=session.filename,
        size=session.size,
        status=session.status,
        chunk_size=session.chunk_size,
        expected_chunks=session.expected_chunks,
        received_chunks=session.received_chunks or [],
    )


@router.put("/{upload_id}/chunk")
def upload_chunk(
    upload_id: uuid.UUID,
    index: int,
    data: bytes = Body(...),
    db: Session = Depends(get_db),
):
    session = db.get(UploadSession, upload_id)
    if not session:
        raise HTTPException(status_code=404, detail="Upload session not found")
    if session.status != "OPEN":
        raise HTTPException(status_code=409, detail="Upload already finalized")
    prefix = Path(session.temp_prefix)
    object_store.write_chunk(prefix, index, data)
    received = set(session.received_chunks or [])
    received.add(index)
    session.received_chunks = sorted(received)
    db.commit()
    return {
        "status": "ok",
        "index": index,
        "received": len(data),
        "received_chunks": session.received_chunks,
    }


@router.post("/{upload_id}/finalize", response_model=SourceFileOut)
def finalize_upload(upload_id: uuid.UUID, db: Session = Depends(get_db)):
    session = db.get(UploadSession, upload_id)
    if not session:
        raise HTTPException(status_code=404, detail="Upload session not found")
    if session.status == "FINALIZED":
        existing = db.query(SourceFile).filter(SourceFile.sha256 == session.final_sha256).one_or_none()
        if existing:
            return SourceFileOut(
                id=existing.id,
                sha256=existing.sha256,
                name=existing.name,
                size=existing.size,
                uri=existing.uri,
                created_at=existing.created_at,
            )
        raise HTTPException(status_code=409, detail="Upload already finalized")
    expected = session.expected_chunks
    if expected is not None and len(session.received_chunks or []) < expected:
        raise HTTPException(status_code=409, detail="Missing chunks")
    prefix = Path(session.temp_prefix)
    chunk_paths = sorted(prefix.glob("chunk_*.part"))
    digest, target, size = object_store.finalize_upload(chunk_paths)
    for path in chunk_paths:
        path.unlink(missing_ok=True)
    try:
        prefix.rmdir()
    except OSError:
        pass
    existing = db.query(SourceFile).filter(SourceFile.sha256 == digest).one_or_none()
    if existing:
        session.status = "FINALIZED"
        session.final_sha256 = digest
        session.final_uri = str(target)
        db.commit()
        return SourceFileOut(
            id=existing.id,
            sha256=existing.sha256,
            name=existing.name,
            size=existing.size,
            uri=existing.uri,
            created_at=existing.created_at,
        )
    source_file = SourceFile(
        sha256=digest,
        name=session.filename,
        size=size,
        uri=str(target),
    )
    session.status = "FINALIZED"
    session.final_sha256 = digest
    session.final_uri = str(target)
    db.add(source_file)
    db.commit()
    db.refresh(source_file)
    return SourceFileOut(
        id=source_file.id,
        sha256=source_file.sha256,
        name=source_file.name,
        size=source_file.size,
        uri=source_file.uri,
        created_at=source_file.created_at,
    )

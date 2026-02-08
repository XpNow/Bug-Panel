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
    temp_path = object_store.create_upload(str(upload_id))
    session = UploadSession(
        id=upload_id,
        filename=payload.filename,
        size=payload.size,
        temp_path=str(temp_path),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return UploadSessionOut(
        id=session.id,
        filename=session.filename,
        size=session.size,
        completed=session.completed,
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
    if session.completed:
        raise HTTPException(status_code=409, detail="Upload already finalized")
    object_store.append_chunk(Path(session.temp_path), data)
    return {"status": "ok", "index": index, "received": len(data)}


@router.post("/{upload_id}/finalize", response_model=SourceFileOut)
def finalize_upload(upload_id: uuid.UUID, db: Session = Depends(get_db)):
    session = db.get(UploadSession, upload_id)
    if not session:
        raise HTTPException(status_code=404, detail="Upload session not found")
    if session.completed:
        raise HTTPException(status_code=409, detail="Upload already finalized")
    digest, target, size = object_store.finalize_upload(Path(session.temp_path), session.filename)
    existing = db.query(SourceFile).filter(SourceFile.sha256 == digest).one_or_none()
    if existing:
        session.completed = True
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
    session.completed = True
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

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..deps import get_db
from ..models import IngestJob, SourceFile, Event, DictEventType
from ..schemas import IngestJobCreate, IngestJobOut

router = APIRouter(prefix="/ingest-jobs", tags=["ingest-jobs"])


@router.post("", response_model=IngestJobOut)
def create_ingest_job(payload: IngestJobCreate, db: Session = Depends(get_db)):
    source_file = db.get(SourceFile, payload.source_file_id)
    if not source_file:
        raise HTTPException(status_code=404, detail="Source file not found")
    job = IngestJob(source_file_id=payload.source_file_id, status="queued")
    db.add(job)
    db.commit()
    db.refresh(job)
    return IngestJobOut(**job.__dict__)


@router.get("", response_model=list[IngestJobOut])
def list_ingest_jobs(db: Session = Depends(get_db)):
    jobs = db.query(IngestJob).order_by(IngestJob.created_at.desc()).all()
    return [IngestJobOut(**job.__dict__) for job in jobs]


@router.get("/{job_id}", response_model=IngestJobOut)
def get_ingest_job(job_id: uuid.UUID, db: Session = Depends(get_db)):
    job = db.get(IngestJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return IngestJobOut(**job.__dict__)


@router.get("/{job_id}/preview")
def preview_events(job_id: uuid.UUID, db: Session = Depends(get_db)):
    job = db.get(IngestJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    events = (
        db.query(Event, DictEventType)
        .join(DictEventType, Event.event_type_id == DictEventType.id)
        .filter(Event.source_file_id == job.source_file_id)
        .order_by(Event.created_at.desc())
        .limit(50)
        .all()
    )
    response = []
    for event, event_type in events:
        response.append(
            {
                "id": event.id,
                "occurred_at": event.occurred_at,
                "occurred_at_quality": event.occurred_at_quality,
                "event_type": event_type.key,
                "src_player_id": event.src_player_id,
                "dst_player_id": event.dst_player_id,
                "amount": float(event.amount) if event.amount is not None else None,
                "qty": float(event.qty) if event.qty is not None else None,
                "raw_block_id": event.raw_block_id,
                "raw_line_index": event.raw_line_index,
            }
        )
    return {"job_id": job_id, "status": job.status, "events": response, "updated_at": datetime.utcnow()}

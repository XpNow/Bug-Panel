from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, aliased

from ..deps import get_db
from ..models import Event, DictEventType, DictPlayer, DictItem, DictContainer
from ..schemas import EventOut

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=list[EventOut])
def list_events(
    db: Session = Depends(get_db),
    event_type: str | None = None,
    player_id: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = Query(default=100, le=500),
    offset: int = 0,
):
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
    if player_id:
        query = query.filter((src_player.player_id == player_id) | (dst_player.player_id == player_id))
    if start:
        query = query.filter(Event.occurred_at >= start)
    if end:
        query = query.filter(Event.occurred_at <= end)
    rows = query.order_by(Event.created_at.desc()).offset(offset).limit(limit).all()
    events = []
    for event, event_type_row, src_player, dst_player, item, container in rows:
        events.append(
            EventOut(
                id=event.id,
                occurred_at=event.occurred_at,
                occurred_at_quality=event.occurred_at_quality,
                event_type=event_type_row.key,
                src_player_id=src_player.player_id if src_player else None,
                dst_player_id=dst_player.player_id if dst_player else None,
                item=item.name if item else None,
                container=container.key if container else None,
                amount=float(event.amount) if event.amount is not None else None,
                qty=float(event.qty) if event.qty is not None else None,
                metadata=event.metadata,
                raw_block_id=event.raw_block_id,
                raw_line_index=event.raw_line_index,
            )
        )
    return events


@router.get("/{event_id}", response_model=EventOut)
def get_event(event_id: uuid.UUID, db: Session = Depends(get_db)):
    src_player = aliased(DictPlayer)
    dst_player = aliased(DictPlayer)
    row = (
        db.query(Event, DictEventType, src_player, dst_player, DictItem, DictContainer)
        .join(DictEventType, Event.event_type_id == DictEventType.id)
        .outerjoin(src_player, Event.src_player_id == src_player.id)
        .outerjoin(dst_player, Event.dst_player_id == dst_player.id)
        .outerjoin(DictItem, Event.item_id == DictItem.id)
        .outerjoin(DictContainer, Event.container_id == DictContainer.id)
        .filter(Event.id == event_id)
        .one_or_none()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Event not found")
    event, event_type_row, src_player, dst_player, item, container = row
    return EventOut(
        id=event.id,
        occurred_at=event.occurred_at,
        occurred_at_quality=event.occurred_at_quality,
        event_type=event_type_row.key,
        src_player_id=src_player.player_id if src_player else None,
        dst_player_id=dst_player.player_id if dst_player else None,
        item=item.name if item else None,
        container=container.key if container else None,
        amount=float(event.amount) if event.amount is not None else None,
        qty=float(event.qty) if event.qty is not None else None,
        metadata=event.metadata,
        raw_block_id=event.raw_block_id,
        raw_line_index=event.raw_line_index,
    )

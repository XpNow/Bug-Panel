from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..deps import get_db
from ..models import DictPlayer, DictAlias

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
def search(q: str = Query(..., min_length=2), db: Session = Depends(get_db)):
    players = (
        db.query(DictPlayer)
        .filter(DictPlayer.player_id.ilike(f"%{q}%"))
        .limit(20)
        .all()
    )
    aliases = (
        db.query(DictAlias)
        .filter(DictAlias.alias.ilike(f"%{q}%"))
        .limit(20)
        .all()
    )
    return {
        "players": [player.player_id for player in players],
        "aliases": [alias.alias for alias in aliases],
    }

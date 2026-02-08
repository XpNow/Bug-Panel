from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass
class PayloadLine:
    text: str
    raw_block_id: str
    raw_line_index: int


@dataclass
class NormalizedBlock:
    title: str | None
    occurred_at: object | None
    occurred_at_quality: str
    payload: list[PayloadLine]


@dataclass
class EventData:
    event_type: str
    src_player_id: str | None = None
    dst_player_id: str | None = None
    item: str | None = None
    container: str | None = None
    amount: float | None = None
    qty: float | None = None
    metadata: dict | None = None
    raw_block_id: str | None = None
    raw_line_index: int | None = None


class Parser:
    parser_id = "base"
    version = "v1"

    def match(self, block: NormalizedBlock) -> bool:
        raise NotImplementedError

    def parse(self, block: NormalizedBlock) -> Iterable[EventData]:
        raise NotImplementedError

from __future__ import annotations

import re
from typing import Iterable

from .base import Parser, NormalizedBlock, EventData

GIVE_MONEY = re.compile(
    r"(?P<staff>.+?)\[(?P<staff_id>\d+)\] i-a dat lui (?P<target>.+?)\[(?P<target_id>\d+)\] suma de (?P<amount>[\d.,]+)\$"
)
GIVE_ITEM = re.compile(
    r"(?P<staff>.+?)\[(?P<staff_id>\d+)\] i-a dat lui (?P<target>.+?)\[(?P<target_id>\d+)\] item-ul (?P<item>.+?)\(x(?P<qty>[\d.,]+)\)"
)


class AdminParser(Parser):
    parser_id = "admin"
    version = "v1"

    def match(self, block: NormalizedBlock) -> bool:
        return (block.title or "").strip() in {"Give Money (K-Menu)", "Give Item (K-Menu)"}

    def parse(self, block: NormalizedBlock) -> Iterable[EventData]:
        for payload in block.payload:
            line = payload.text
            if match := GIVE_MONEY.search(line):
                yield EventData(
                    event_type="ADMIN_GIVE_MONEY",
                    src_player_id=match.group("staff_id"),
                    dst_player_id=match.group("target_id"),
                    amount=_parse_amount(match.group("amount")),
                    metadata={"staff_rank": _extract_rank(match.group("staff"))},
                    raw_block_id=payload.raw_block_id,
                    raw_line_index=payload.raw_line_index,
                )
            elif match := GIVE_ITEM.search(line):
                yield EventData(
                    event_type="ADMIN_GIVE_ITEM",
                    src_player_id=match.group("staff_id"),
                    dst_player_id=match.group("target_id"),
                    item=match.group("item").strip(),
                    qty=_parse_amount(match.group("qty")),
                    metadata={"staff_rank": _extract_rank(match.group("staff"))},
                    raw_block_id=payload.raw_block_id,
                    raw_line_index=payload.raw_line_index,
                )


def _parse_amount(value: str) -> float:
    return float(value.replace(".", "").replace(",", "."))


def _extract_rank(name: str) -> str | None:
    if "Fondator" in name:
        return "Fondator"
    if "Admin" in name:
        return "Admin"
    return None

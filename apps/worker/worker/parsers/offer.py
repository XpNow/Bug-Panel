from __future__ import annotations

import re
from typing import Iterable

from .base import Parser, NormalizedBlock, EventData

MONEY = re.compile(
    r"Jucatorul (?P<src>.+?)\[(?P<src_id>\d+)\] i-a oferit lui (?P<dst>.+?)\[(?P<dst_id>\d+)\] suma de (?P<amount>[\d.,]+)\$\."
)
ITEM = re.compile(
    r"Jucatorul (?P<src>.+?)\[(?P<src_id>\d+)\] i-a oferit lui (?P<dst>.+?)\[(?P<dst_id>\d+)\] - (?P<item>.+?)\(x(?P<qty>[\d.,]+)\)\."
)


class OfferParser(Parser):
    parser_id = "offer"
    version = "v1"

    def match(self, block: NormalizedBlock) -> bool:
        return (block.title or "").strip() in {"Ofera Bani", "Ofera Item"}

    def parse(self, block: NormalizedBlock) -> Iterable[EventData]:
        for payload in block.payload:
            line = payload.text
            if match := MONEY.search(line):
                yield EventData(
                    event_type="OFFER_MONEY",
                    src_player_id=match.group("src_id"),
                    dst_player_id=match.group("dst_id"),
                    amount=_parse_amount(match.group("amount")),
                    raw_block_id=payload.raw_block_id,
                    raw_line_index=payload.raw_line_index,
                )
            elif match := ITEM.search(line):
                item = match.group("item").strip()
                metadata = {}
                if item.lower() == "nil":
                    metadata["item_unknown"] = True
                    item = None
                yield EventData(
                    event_type="OFFER_ITEM",
                    src_player_id=match.group("src_id"),
                    dst_player_id=match.group("dst_id"),
                    item=item,
                    qty=_parse_amount(match.group("qty")),
                    metadata=metadata or None,
                    raw_block_id=payload.raw_block_id,
                    raw_line_index=payload.raw_line_index,
                )


def _parse_amount(value: str) -> float:
    return float(value.replace(".", "").replace(",", "."))

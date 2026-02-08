from __future__ import annotations

import re
from typing import Iterable

from .base import Parser, NormalizedBlock, EventData
from .utils import parse_int_value

BUY = re.compile(
    r"Juc(?:ător|ator): (?P<name>.+?)\((?P<id>\d+)\) a cumparat (?P<item>.+?) pentru suma de (?P<amount>[\d.,]+)\$"
)


class JewelryParser(Parser):
    parser_id = "jewelry"
    version = "v1"

    def match(self, block: NormalizedBlock) -> bool:
        return (block.title or "").strip() == "💎 Bijuterii"

    def parse(self, block: NormalizedBlock) -> Iterable[EventData]:
        for payload in block.payload:
            if match := BUY.search(payload.text):
                yield EventData(
                    event_type="JEWELRY_BUY",
                    src_player_id=match.group("id"),
                    item=match.group("item").strip(),
                    money=parse_int_value(match.group("amount")),
                    raw_block_id=payload.raw_block_id,
                    raw_line_index=payload.raw_line_index,
                    global_line_no=payload.global_line_no,
                )

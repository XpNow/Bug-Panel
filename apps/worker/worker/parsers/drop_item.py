from __future__ import annotations

import re
from typing import Iterable

from .base import Parser, NormalizedBlock, EventData
from .utils import parse_int_value

DROP = re.compile(
    r"Juc(?:ător|ator): (?P<name>.+?) \((?P<id>\d+)\) a aruncat pe jos (?P<qty>[\d.,]+)x (?P<item>.+)"
)


class DropItemParser(Parser):
    parser_id = "drop-item"
    version = "v1"

    def match(self, block: NormalizedBlock) -> bool:
        return (block.title or "").strip() == "⚠️ Obiect aruncat pe jos"

    def parse(self, block: NormalizedBlock) -> Iterable[EventData]:
        for payload in block.payload:
            if match := DROP.search(payload.text):
                yield EventData(
                    event_type="ITEM_DROP",
                    src_player_id=match.group("id"),
                    container="ground",
                    item=match.group("item").strip(),
                    qty=parse_int_value(match.group("qty")),
                    raw_block_id=payload.raw_block_id,
                    raw_line_index=payload.raw_line_index,
                    global_line_no=payload.global_line_no,
                )

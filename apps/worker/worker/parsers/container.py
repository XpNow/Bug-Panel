from __future__ import annotations

import re
from typing import Iterable

from .base import Parser, NormalizedBlock, EventData
from .utils import parse_int_value

PUT = re.compile(
    r"\[TRANSFER\].*?\[(?P<id>\d+)\] a pus in (?P<container>.+?) item-ul (?P<item>.+?)\(x(?P<qty>[\d.,]+)\)\."
)
TAKE = re.compile(
    r"\[REMOVE\].*?\[(?P<id>\d+)\] a scos din (?P<container>.+?) item-ul (?P<item>.+?)\(x(?P<qty>[\d.,]+)\)\."
)
SEARCH = re.compile(
    r"\[PERCHEZITIE\] Jucatorul (?P<name>.+?)\[(?P<sid>\d+)\] a scos din (?P<target>.+?) item-ul (?P<item>.+?)\(x(?P<qty>[\d.,]+)\)\."
)


class ContainerParser(Parser):
    parser_id = "container"
    version = "v1"

    def match(self, block: NormalizedBlock) -> bool:
        return (block.title or "").strip() == "Transfera Item"

    def parse(self, block: NormalizedBlock) -> Iterable[EventData]:
        for payload in block.payload:
            line = payload.text
            if match := PUT.search(line):
                yield EventData(
                    event_type="CONTAINER_PUT",
                    src_player_id=match.group("id"),
                    container=match.group("container").strip(),
                    item=match.group("item").strip(),
                    qty=parse_int_value(match.group("qty")),
                    raw_block_id=payload.raw_block_id,
                    raw_line_index=payload.raw_line_index,
                    global_line_no=payload.global_line_no,
                )
            elif match := TAKE.search(line):
                yield EventData(
                    event_type="CONTAINER_TAKE",
                    src_player_id=match.group("id"),
                    container=match.group("container").strip(),
                    item=match.group("item").strip(),
                    qty=parse_int_value(match.group("qty")),
                    raw_block_id=payload.raw_block_id,
                    raw_line_index=payload.raw_line_index,
                    global_line_no=payload.global_line_no,
                )
            elif match := SEARCH.search(line):
                yield EventData(
                    event_type="SEARCH_TAKE",
                    src_player_id=match.group("sid"),
                    dst_player_id=match.group("target").strip(),
                    item=match.group("item").strip(),
                    qty=parse_int_value(match.group("qty")),
                    raw_block_id=payload.raw_block_id,
                    raw_line_index=payload.raw_line_index,
                    global_line_no=payload.global_line_no,
                )

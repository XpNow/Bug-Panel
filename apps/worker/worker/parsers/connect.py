from __future__ import annotations

import re
from typing import Iterable

from .base import Parser, NormalizedBlock, EventData

CONNECT = re.compile(r"(?P<name>.+?)\[(?P<id>\d+)\] se conectează cu succes \| \(ip: (?P<ip>.+?)\)")
DISCONNECT = re.compile(r"(?P<name>.+?)\[(?P<id>\d+)\] s-a deconectat (?P<rest>.+)")


class ConnectParser(Parser):
    parser_id = "connect"
    version = "v1"

    def match(self, block: NormalizedBlock) -> bool:
        return (block.title or "").strip() in {"Server Connect", "Server Disconnect"}

    def parse(self, block: NormalizedBlock) -> Iterable[EventData]:
        for payload in block.payload:
            line = payload.text
            if match := CONNECT.search(line):
                yield EventData(
                    event_type="CONNECT",
                    src_player_id=match.group("id"),
                    metadata={"ip": match.group("ip")},
                    raw_block_id=payload.raw_block_id,
                    raw_line_index=payload.raw_line_index,
                )
            elif match := DISCONNECT.search(line):
                event_type = "DISCONNECT"
                metadata = {"reason_raw": match.group("rest")}
                if "banat" in line.lower():
                    event_type = "DISCONNECT_BANNED"
                yield EventData(
                    event_type=event_type,
                    src_player_id=match.group("id"),
                    metadata=metadata,
                    raw_block_id=payload.raw_block_id,
                    raw_line_index=payload.raw_line_index,
                )

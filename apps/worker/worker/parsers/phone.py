from __future__ import annotations

import re
from typing import Iterable

from .base import Parser, NormalizedBlock, EventData
from .utils import parse_int_value

DELTA = re.compile(
    r"Juc(?:ătorului|atorului): (?P<name>.+?)\((?P<id>\d+)\) i-au fost (?P<action>luati|adaugati) (?P<amount>[\d.,]+) \$"
)


class PhoneParser(Parser):
    parser_id = "phone"
    version = "v1"

    def match(self, block: NormalizedBlock) -> bool:
        return (block.title or "").strip() == "💵 Telefon"

    def parse(self, block: NormalizedBlock) -> Iterable[EventData]:
        debits: list[tuple[str, int, str, int, int]] = []
        credits: list[tuple[str, int, str, int, int]] = []
        for payload in block.payload:
            line = payload.text
            if match := DELTA.search(line):
                amount = parse_int_value(match.group("amount"))
                player_id = match.group("id")
                if match.group("action") == "luati":
                    debits.append(
                        (
                            player_id,
                            amount,
                            payload.raw_block_id,
                            payload.raw_line_index,
                            payload.global_line_no,
                        )
                    )
                else:
                    credits.append(
                        (
                            player_id,
                            amount,
                            payload.raw_block_id,
                            payload.raw_line_index,
                            payload.global_line_no,
                        )
                    )

        used_credit = set()
        for debit in debits:
            debit_id, amount, raw_block_id, raw_line_index, global_line_no = debit
            paired_index = None
            for idx, credit in enumerate(credits):
                if idx in used_credit:
                    continue
                if credit[1] == amount:
                    paired_index = idx
                    break
            if paired_index is not None:
                credit = credits[paired_index]
                used_credit.add(paired_index)
                yield EventData(
                    event_type="PHONE_TRANSFER",
                    src_player_id=debit_id,
                    dst_player_id=credit[0],
                    money=amount,
                    raw_block_id=raw_block_id,
                    raw_line_index=raw_line_index,
                    global_line_no=global_line_no,
                )
            else:
                yield EventData(
                    event_type="PHONE_DELTA",
                    src_player_id=debit_id,
                    money=amount,
                    metadata={"sign": "debit"},
                    raw_block_id=raw_block_id,
                    raw_line_index=raw_line_index,
                    global_line_no=global_line_no,
                )

        for idx, credit in enumerate(credits):
            if idx in used_credit:
                continue
            yield EventData(
                event_type="PHONE_DELTA",
                src_player_id=credit[0],
                money=credit[1],
                metadata={"sign": "credit"},
                raw_block_id=credit[2],
                raw_line_index=credit[3],
                global_line_no=credit[4],
            )

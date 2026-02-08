from __future__ import annotations

import re
from typing import Iterable

from .base import Parser, NormalizedBlock, EventData
from .utils import parse_int_value

WITHDRAW = re.compile(r"(?P<name>.+?)\[(?P<id>\d+)\] a retras (?P<amount>[\d.,]+)\$")
DEPOSIT = re.compile(r"(?P<name>.+?)\[(?P<id>\d+)\] a depozitat (?P<amount>[\d.,]+)\$")
TRANSFER = re.compile(
    r"(?P<src>.+?)\[(?P<src_id>\d+)\] a transferat (?P<amount>[\d.,]+)\$ lui (?P<dst>.+?)\[(?P<dst_id>\d+)\]\.?"
)


class BankParser(Parser):
    parser_id = "bank"
    version = "v1"

    def match(self, block: NormalizedBlock) -> bool:
        return (block.title or "").strip() in {
            "Retragere Banca",
            "Depunere Banca",
            "Transfer (Bancar)",
        }

    def parse(self, block: NormalizedBlock) -> Iterable[EventData]:
        for payload in block.payload:
            line = payload.text
            if match := WITHDRAW.search(line):
                yield EventData(
                    event_type="BANK_WITHDRAW",
                    src_player_id=match.group("id"),
                    money=parse_int_value(match.group("amount")),
                    raw_block_id=payload.raw_block_id,
                    raw_line_index=payload.raw_line_index,
                    global_line_no=payload.global_line_no,
                )
            elif match := DEPOSIT.search(line):
                yield EventData(
                    event_type="BANK_DEPOSIT",
                    src_player_id=match.group("id"),
                    money=parse_int_value(match.group("amount")),
                    raw_block_id=payload.raw_block_id,
                    raw_line_index=payload.raw_line_index,
                    global_line_no=payload.global_line_no,
                )
            elif match := TRANSFER.search(line):
                yield EventData(
                    event_type="BANK_TRANSFER",
                    src_player_id=match.group("src_id"),
                    dst_player_id=match.group("dst_id"),
                    money=parse_int_value(match.group("amount")),
                    raw_block_id=payload.raw_block_id,
                    raw_line_index=payload.raw_line_index,
                    global_line_no=payload.global_line_no,
                )

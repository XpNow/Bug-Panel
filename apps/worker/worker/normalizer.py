from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterator
from zoneinfo import ZoneInfo

from dateutil import parser as date_parser

from .parsers.base import NormalizedBlock, PayloadLine

TIMEZONE = ZoneInfo("Europe/Bucharest")

TIMESTAMP_STYLE_A = re.compile(r"^—\s*(?P<ts>.+)$")
TIMESTAMP_STYLE_B = re.compile(r"^Made by Synked•(?P<ts>.+)$")
NOISE_LINES = {
    "Made by Synked with ❤️ & ☕",
}

KNOWN_TITLES = {
    "Retragere Banca",
    "Depunere Banca",
    "Transfer (Bancar)",
    "Ofera Bani",
    "Ofera Item",
    "💵 Telefon",
    "⚠️ Obiect aruncat pe jos",
    "Transfera Item",
    "Server Connect",
    "Server Disconnect",
    "Give Money (K-Menu)",
    "Give Item (K-Menu)",
    "💎 Bijuterii",
}


@dataclass
class BlockState:
    occurred_at: datetime | None
    occurred_at_quality: str
    title: str | None
    payload: list[PayloadLine]


def normalize_lines(lines: Iterator[tuple[str, str, int]], job_date: datetime, date_order: str = "DMY"):
    state = BlockState(occurred_at=None, occurred_at_quality="UNKNOWN", title=None, payload=[])
    last_absolute: datetime | None = None

    def flush_state():
        nonlocal state
        if state.title or state.payload:
            yield NormalizedBlock(
                title=state.title,
                occurred_at=state.occurred_at,
                occurred_at_quality=state.occurred_at_quality,
                payload=state.payload,
            )
        state = BlockState(occurred_at=None, occurred_at_quality="UNKNOWN", title=None, payload=[])

    for raw_text, raw_block_id, raw_line_index in lines:
        line = raw_text.strip()
        if not line:
            continue
        if line in NOISE_LINES:
            continue

        timestamp_match = TIMESTAMP_STYLE_A.match(line) or TIMESTAMP_STYLE_B.match(line)
        if timestamp_match:
            for block in flush_state():
                yield block
            ts_text = timestamp_match.group("ts").strip()
            occurred_at, quality, last_absolute = parse_timestamp(
                ts_text, last_absolute, job_date, date_order
            )
            state.occurred_at = occurred_at
            state.occurred_at_quality = quality
            state.title = None
            continue

        if state.title is None and (line in KNOWN_TITLES or _looks_like_title(line)):
            state.title = line
            continue

        cleaned = clean_payload_line(line)
        state.payload.append(
            PayloadLine(text=cleaned, raw_block_id=raw_block_id, raw_line_index=raw_line_index)
        )

    for block in flush_state():
        yield block


def parse_timestamp(
    ts_text: str,
    last_absolute: datetime | None,
    job_date: datetime,
    date_order: str,
) -> tuple[datetime | None, str, datetime | None]:
    ts_text = ts_text.replace("at ", "")
    ts_lower = ts_text.lower()
    anchor = last_absolute or job_date
    if re.match(r"^\\d{1,2}:\\d{2}(\\s*[APap][Mm])?$", ts_text.strip()):
        dt = _parse_time_only(ts_text, anchor.date())
        return dt, "TIME_ONLY", last_absolute
    if "yesterday" in ts_lower:
        base = (anchor - timedelta(days=1)).date()
        time_part = ts_text.split("at")[-1].strip()
        dt = _parse_time_only(time_part, base)
        return dt, "RELATIVE", last_absolute
    if "today" in ts_lower:
        base = anchor.date()
        time_part = ts_text.split("at")[-1].strip()
        dt = _parse_time_only(time_part, base)
        return dt, "RELATIVE", last_absolute
    try:
        dt = date_parser.parse(ts_text, dayfirst=(date_order == "DMY"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=TIMEZONE)
        last_absolute = dt
        return dt, "ABSOLUTE", last_absolute
    except (ValueError, TypeError):
        return None, "UNKNOWN", last_absolute


def _parse_time_only(time_part: str, base_date):
    dt = date_parser.parse(time_part)
    dt = datetime.combine(base_date, dt.time()).replace(tzinfo=TIMEZONE)
    return dt


def clean_payload_line(line: str) -> str:
    line = re.sub(r"<@!?\d+>", "", line)
    line = line.replace("**", "").replace("*", "")
    line = line.replace("`", "")
    return line.strip()


def _looks_like_title(line: str) -> bool:
    if line.startswith("⚠️") or line.startswith("💵") or line.startswith("💎"):
        return True
    if "(" in line and ")" in line and len(line) < 40:
        return True
    return False

from __future__ import annotations

import re


def parse_int_value(value: str) -> int:
    cleaned = value.strip()
    cleaned = cleaned.replace("$", "")
    cleaned = re.sub(r"[^\d]", "", cleaned)
    return int(cleaned) if cleaned else 0

from __future__ import annotations

import os
from pathlib import Path

OBJECT_STORE_PATH = Path(os.getenv("OBJECT_STORE_PATH", "/data/object-store"))


class LocalObjectStore:
    def __init__(self) -> None:
        OBJECT_STORE_PATH.mkdir(parents=True, exist_ok=True)

    def raw_block_path(self, source_file_id: str, block_id: str) -> Path:
        target = OBJECT_STORE_PATH / "raw-blocks" / str(source_file_id) / f"{block_id}.zst"
        target.parent.mkdir(parents=True, exist_ok=True)
        return target


object_store = LocalObjectStore()

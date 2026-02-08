from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import BinaryIO

OBJECT_STORE_PATH = Path(os.getenv("OBJECT_STORE_PATH", "/data/object-store"))
UPLOAD_PATH = Path(os.getenv("UPLOAD_PATH", "/data/uploads"))


class LocalObjectStore:
    def __init__(self) -> None:
        OBJECT_STORE_PATH.mkdir(parents=True, exist_ok=True)
        UPLOAD_PATH.mkdir(parents=True, exist_ok=True)

    def create_upload(self, upload_id: str) -> Path:
        target = UPLOAD_PATH / f"{upload_id}.upload"
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    def append_chunk(self, target: Path, data: bytes) -> None:
        with target.open("ab") as handle:
            handle.write(data)

    def finalize_upload(self, upload_path: Path, filename: str) -> tuple[str, Path, int]:
        sha256 = hashlib.sha256()
        size = 0
        with upload_path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                sha256.update(chunk)
                size += len(chunk)
        digest = sha256.hexdigest()
        target = OBJECT_STORE_PATH / "source-files" / digest
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            upload_path.replace(target)
        else:
            upload_path.unlink(missing_ok=True)
        return digest, target, size

    def open_raw_block(self, uri: str) -> BinaryIO:
        return Path(uri).open("rb")

    def get_report_pack_path(self, name: str) -> Path:
        target = OBJECT_STORE_PATH / "report-packs" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        return target


object_store = LocalObjectStore()

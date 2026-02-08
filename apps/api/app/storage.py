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

    def create_upload_prefix(self, upload_id: str) -> Path:
        target = UPLOAD_PATH / upload_id
        target.mkdir(parents=True, exist_ok=True)
        return target

    def write_chunk(self, prefix: Path, index: int, data: bytes) -> Path:
        chunk_path = prefix / f"chunk_{index:06d}.part"
        with chunk_path.open("wb") as handle:
            handle.write(data)
        return chunk_path

    def finalize_upload(self, chunk_paths: list[Path]) -> tuple[str, Path, int]:
        sha256 = hashlib.sha256()
        size = 0
        target = OBJECT_STORE_PATH / "source-files"
        target.mkdir(parents=True, exist_ok=True)
        temp_path = target / f"tmp-{hashlib.sha256(os.urandom(8)).hexdigest()}"
        with temp_path.open("wb") as output:
            for path in chunk_paths:
                with path.open("rb") as handle:
                    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                        sha256.update(chunk)
                        size += len(chunk)
                        output.write(chunk)
        digest = sha256.hexdigest()
        final_path = target / digest
        if not final_path.exists():
            temp_path.replace(final_path)
        else:
            temp_path.unlink(missing_ok=True)
        return digest, final_path, size

    def open_raw_block(self, uri: str) -> BinaryIO:
        return Path(uri).open("rb")

    def get_report_pack_path(self, name: str) -> Path:
        target = OBJECT_STORE_PATH / "report-packs" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        return target


object_store = LocalObjectStore()

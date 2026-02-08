from __future__ import annotations

import json
import os
from pathlib import Path

import requests

API_BASE = os.getenv("API_BASE", "http://localhost:8000")
SAMPLE_PATH = Path(__file__).parent / "sample_transcript.txt"
CHUNK_SIZE = 1024 * 1024


def main() -> None:
    size = SAMPLE_PATH.stat().st_size
    response = requests.post(
        f"{API_BASE}/uploads/create", json={"filename": SAMPLE_PATH.name, "size": size}
    )
    response.raise_for_status()
    upload_id = response.json()["id"]

    with SAMPLE_PATH.open("rb") as handle:
        index = 0
        while True:
            chunk = handle.read(CHUNK_SIZE)
            if not chunk:
                break
            put = requests.put(
                f"{API_BASE}/uploads/{upload_id}/chunk",
                params={"index": index},
                data=chunk,
            )
            put.raise_for_status()
            index += 1

    finalize = requests.post(f"{API_BASE}/uploads/{upload_id}/finalize")
    finalize.raise_for_status()
    source_file = finalize.json()

    job = requests.post(
        f"{API_BASE}/ingest-jobs", json={"source_file_id": source_file["id"]}
    )
    job.raise_for_status()
    print(json.dumps(job.json(), indent=2))


if __name__ == "__main__":
    main()

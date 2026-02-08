from __future__ import annotations

import time

from .db import SessionLocal
from .ingest import IngestRunner


POLL_INTERVAL = 2


def main() -> None:
    while True:
        with SessionLocal() as db:
            runner = IngestRunner(db)
            ran = runner.run_next_job()
        if not ran:
            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()

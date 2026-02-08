from __future__ import annotations

from fastapi import FastAPI

from .routers import uploads, ingest_jobs, events, evidence, report_packs, search

app = FastAPI(title="Phoenix Investigation Panel V2 API")

app.include_router(uploads.router)
app.include_router(ingest_jobs.router)
app.include_router(events.router)
app.include_router(search.router)
app.include_router(evidence.router)
app.include_router(report_packs.router)

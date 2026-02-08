# Phoenix Investigation Panel V2 (phx-tool-v2)

Phoenix Investigation Panel V2 este un panel web pentru analiza logurilor FiveM RP, cu ingest streaming, evidence drill-down si stocare compacta pe blocuri comprimate.

## Highlights

- Upload chunked (5GB+) + ingest pornit din UI/API.
- Evidence-first: fiecare event are pointer la raw block + line index, iar API-ul returneaza contextul.
- Compact: raw text in blocuri zstd in object store, metadata in Postgres.
- Imutabil + idempotent: reprocess prin job nou si dedupe pe hash.
- Parsare streaming cu state machine pentru formatele Discord (stil A/B).

## Structura repo

- `apps/api` - FastAPI + Alembic + REST endpoints.
- `apps/worker` - worker streaming, parsers, normalizer, object store.
- `apps/web` - Next.js App Router dashboard.
- `scripts` - script ingest sample + transcript sample.

## Rulare locala (docker-compose)

```bash
# porneste postgres, api, worker si web

docker compose up --build
```

### Migrations

```bash
cd apps/api
alembic upgrade head
```

## Ingest sample

```bash
python scripts/ingest_sample.py
```

## Endpointuri MVP

- Upload:
  - `POST /uploads/create`
  - `PUT /uploads/{id}/chunk?index=`
  - `POST /uploads/{id}/finalize`
- Ingest:
  - `POST /ingest-jobs`
  - `GET /ingest-jobs`
  - `GET /ingest-jobs/{id}`
  - `GET /ingest-jobs/{id}/preview`
- Events:
  - `GET /events`
  - `GET /events/{event_id}`
- Search:
  - `GET /search?q=`
- Evidence:
  - `GET /evidence/raw-line?raw_block_id=&line_index=&context=2`
- Report packs:
  - `POST /report-packs`
  - `GET /report-packs`
  - `GET /report-packs/{id}`
  - `GET /report-packs/{id}/download`
  - `GET /report-packs/{id}/file?path=...`

## Note tehnice

- Partitionare events: tabela `event` este partitionata lunar + default partition `event_notime`.
- `date_order=DMY` este default pentru timestamps; poate fi extins in worker config.
- Object store local: `./data/object-store` (MVP), usor de inlocuit cu S3/MinIO.

## UI (MVP)

- Dashboard, Imports, Events Explorer, Players, Containers, Report Packs.
- Evidence Drawer este expus prin endpointul `/evidence/raw-line`.

## Worker

Worker-ul ruleaza polling pe `ingest_job.status = queued`, parseaza streaming, creeaza raw blocks zstd, dedupe events si actualizeaza stats.

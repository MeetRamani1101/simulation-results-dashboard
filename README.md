# Engineering Simulation Results Dashboard

A dashboard for reviewing CAE frequency-response simulation results across
revisions: imports per-revision CSVs into a database, serves them through a
FastAPI backend, and presents them in a React dashboard for comparing
revisions, tracing components across history, and tracking engineering
follow-up ("demand") items.

## Stack

- **Backend**: Python 3.13, FastAPI, SQLAlchemy 2.0, SQLite, pytest
- **Frontend**: React 19, Vite, React Router, Recharts

## Project layout

```text
backend/
  app/
    main.py              FastAPI app, CORS, startup ingestion
    config.py             Env-driven settings (data root, DB URL, review rule)
    models.py              SQLAlchemy models (Project, Component, Revision, Sample, Demand, ImportRun)
    schemas.py              Pydantic response/request models
    crud.py                   ORM -> API schema shaping
    database.py                 Engine/session setup
    ingestion/
      discovery.py               Walks the data root, discovers project/revision/component CSVs
      parser.py                   Validates and parses one CSV
      importer.py                  Orchestrates discovery + parsing + DB upsert, idempotent
    services/
      assessment.py                 Pure pass/fail + peak calculation (the engineering review rule)
    routers/                         FastAPI route handlers (projects, components, revisions, demands, ingest)
    ingest_cli.py                     `python -m app.ingest_cli` - manual ingestion trigger
    seed_cli.py                       `python -m app.seed_cli` - optional example demand seeding
  data/raw/HeadlampAssembly/...       Sample input data (copied from the supplied Inputs/)
  tests/                              pytest suite
frontend/
  src/
    api/client.js                     Typed fetch wrapper for the backend API
    components/                       FrequencyChart, badges, layout, demand modal
    pages/                            Dashboard (projects/components), Component detail, Demands
```

## Running the backend

Requires **Python 3.11-3.13** (pydantic-core currently has no prebuilt wheel
for 3.14 on Windows and fails to build without a Rust toolchain - use 3.13 if
you have multiple versions installed, e.g. `py -3.13`).

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows; use `source .venv/bin/activate` on macOS/Linux
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

On startup the app automatically runs an ingestion pass over `backend/data/raw`
(see **Data ingestion** below) and creates `backend/data/app.db` if it doesn't
exist. API docs are then available at `http://localhost:8000/docs`.

Optional: seed three example demands (one per component, from each
component's first revision) to see the demand-tracking workflow populated:

```bash
python -m app.seed_cli
```

### Running backend tests

```bash
cd backend
.venv\Scripts\activate
python -m pytest -q
```

33 tests cover the assessment rule (boundary conditions at 0/50 Hz and the
15 mm limit), CSV validation (malformed/missing/empty files), ingestion
idempotency (re-import, changed-file re-import, natural revision ordering,
project/revision folder layouts), and the API (comparisons, demand creation
and traceability, filtering).

## Running the frontend

```bash
cd frontend
npm install
npm run dev
```

Opens at `http://localhost:5173`. It expects the backend at
`http://localhost:8000` (see `frontend/.env.development`; override with
`VITE_API_BASE_URL` for a different backend address).

## Data ingestion

The importer scans `SIM_DATA_ROOT` (default `backend/data/raw`) for CSV
files and discovers projects/revisions/components **from the folder
structure** - nothing is hard-coded. Two layouts are supported, auto-detected
per file:

```text
<root>/<revision>/<component>.csv              single implicit project
<root>/<project>/<revision>/<component>.csv     explicit project folder
```

Optionally, a reference photo of the physical component can sit next to its
revision folders (`<project dir>/<component>.png|.jpg|.jpeg|.webp`, e.g.
`backend/data/raw/HeadlampAssembly/Bracket.png`) and it will be served at
`GET /api/components/{id}/image` and shown in the dashboard. Components
without a matching image simply show none - this is discovered the same way
as the CSVs, not hard-coded per component name.

It is triggered three ways, all calling the same idempotent `run_import`:

1. **Automatically on backend startup.**
2. **On demand from the UI** - the "Sync data" button in the sidebar calls
   `POST /api/ingest/run` and shows the resulting counts/errors.
3. **From the command line** - `python -m app.ingest_cli` (useful for a cron
   job or scheduled task against a live data root).

Each file's content hash is stored on its revision row. Re-running the
import is always safe: unchanged files are skipped, changed files have their
samples replaced in place (no duplicate revisions), and new revisions/
components/projects are created as needed. Files that fail validation (wrong
column count, non-numeric values, empty file, CSV dropped directly at the
data root with no revision folder, etc.) are reported - not silently
skipped or partially imported - and recorded in an `ImportRun` row
(`GET /api/ingest/runs`, `GET /api/ingest/runs/latest`).

## Using the dashboard

1. **Projects** (`/`) - pick a project, see each component's latest
   pass/fail result and peak value at a glance.
2. **Component detail** (`/components/:id`) - toggle which revisions are
   overlaid on the frequency-response chart (shaded 0-50 Hz assessment band,
   dashed 15 mm limit line, peak markers), and see the full revision
   comparison table with deltas vs. the previous revision. Click
   **Create demand** on any failing revision to raise a follow-up item
   pre-filled with that finding.
3. **Demands** (`/demands`) - filterable table of all engineering follow-up
   items. Expand a row to see the linked component's result in every
   revision (with the originating finding marked), edit the description,
   change status (Open / In Progress / Resolved - never auto-resolved by a
   later passing result), or jump to the component's comparison view. Use
   **New demand** to create a manual (non-finding) entry.

## API summary

| Endpoint | Purpose |
|---|---|
| `GET /api/projects` | List projects |
| `GET /api/projects/{id}` | Project detail with components + latest revision summary |
| `GET /api/components/{id}/revisions` | A component's revisions, ordered |
| `GET /api/components/{id}/compare?revision_ids=1,2,3` | Samples + assessment + deltas for comparison (defaults to all revisions) |
| `GET /api/revisions/{id}` | One revision's full samples + assessment |
| `GET /api/demands` | List demands, filterable by `status`, `project_id`, `component_id` |
| `POST /api/demands` | Create a demand (manual, or from `origin_revision_id`) |
| `GET /api/demands/{id}` | Demand detail incl. per-revision result trace |
| `PATCH /api/demands/{id}` | Update description/status |
| `POST /api/ingest/run` | Trigger a sync pass |
| `GET /api/ingest/runs` | Recent import run history/errors |

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import CORS_ORIGINS, RUN_INGEST_ON_STARTUP
from .database import SessionLocal, init_db
from .ingestion.importer import persist_report, run_import
from .routers import components, demands, ingest, projects, revisions

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if RUN_INGEST_ON_STARTUP:
        db = SessionLocal()
        try:
            report = run_import(db)
            persist_report(db, report)
            logger.info(
                "Startup ingest: scanned=%s imported=%s updated=%s unchanged=%s errors=%s",
                report.files_scanned,
                report.imported,
                report.updated,
                report.unchanged,
                len(report.errors),
            )
            for err in report.errors:
                logger.warning("Ingest error: %s - %s", err.path, err.message)
        finally:
            db.close()
    yield


app = FastAPI(
    title="Simulation Results Dashboard API",
    description=(
        "Serves imported CAE frequency-response simulation data (projects, "
        "components, revisions, comparisons) and engineering demands from a "
        "SQLite database. CSV inputs are ingested via POST /api/ingest/run "
        "(also run once automatically on startup)."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(components.router)
app.include_router(revisions.router)
app.include_router(demands.router)
app.include_router(ingest.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}

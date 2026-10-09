from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..ingestion.importer import persist_report, run_import

router = APIRouter(prefix="/api/ingest", tags=["ingest"])


@router.post("/run", response_model=schemas.ImportRunOut)
def trigger_ingest(db: Session = Depends(get_db)):
    """Manually trigger a sync of the CSV data root into the database.

    Safe to call repeatedly: unchanged files are skipped, changed files are
    re-imported in place, and files that fail validation are reported back
    (and recorded) without affecting previously-imported data.
    """
    report = run_import(db)
    run = persist_report(db, report)
    return run


@router.get("/runs", response_model=list[schemas.ImportRunOut])
def list_import_runs(db: Session = Depends(get_db)):
    runs = db.query(models.ImportRun).order_by(models.ImportRun.started_at.desc()).limit(20).all()
    return runs


@router.get("/runs/latest", response_model=schemas.ImportRunOut | None)
def latest_import_run(db: Session = Depends(get_db)):
    return (
        db.query(models.ImportRun).order_by(models.ImportRun.started_at.desc()).first()
    )

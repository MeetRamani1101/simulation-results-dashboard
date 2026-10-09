"""Ingestion orchestration: discover CSVs, validate, and upsert into the DB.

Safe to re-run at any time (manually, on a schedule, or on app startup):
- Unchanged files (same content hash) are skipped without touching the DB.
- Changed files have their samples replaced and summary recomputed; the
  revision row (and therefore anything linking to it, like demands) is kept.
- New revision/component/project rows are created as needed.
- Files that fail validation are reported in the returned/stored ImportRun
  and do not affect previously-imported data for that revision.
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy.orm import Session

from .. import models
from ..config import DATA_ROOT
from ..services.assessment import assess_samples
from .discovery import discover_csv_files, natural_sort_key, orphan_csv_files
from .parser import CsvValidationError, parse_results_csv

logger = logging.getLogger(__name__)


@dataclass
class ImportError_:
    path: str
    message: str


@dataclass
class ImportReport:
    data_root: str
    files_scanned: int = 0
    imported: int = 0
    updated: int = 0
    unchanged: int = 0
    errors: list[ImportError_] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "data_root": self.data_root,
            "files_scanned": self.files_scanned,
            "imported": self.imported,
            "updated": self.updated,
            "unchanged": self.unchanged,
            "error_count": len(self.errors),
            "errors": [{"path": e.path, "message": e.message} for e in self.errors],
        }


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _get_or_create_project(db: Session, name: str, source_dir: Path) -> models.Project:
    project = db.query(models.Project).filter(models.Project.name == name).one_or_none()
    if project is None:
        project = models.Project(name=name, source_dir=str(source_dir))
        db.add(project)
        db.flush()
    elif project.source_dir != str(source_dir):
        project.source_dir = str(source_dir)
    return project


def _get_or_create_component(db: Session, project: models.Project, name: str) -> models.Component:
    component = (
        db.query(models.Component)
        .filter(models.Component.project_id == project.id, models.Component.name == name)
        .one_or_none()
    )
    if component is None:
        component = models.Component(project_id=project.id, name=name)
        db.add(component)
        db.flush()
    return component


def _resequence_revisions(db: Session, component: models.Component) -> None:
    """Keep revision.sequence consistent with a natural sort of labels, so
    display order is correct (rev2 < rev10) even as new revisions arrive."""
    revisions = (
        db.query(models.Revision).filter(models.Revision.component_id == component.id).all()
    )
    for rank, revision in enumerate(sorted(revisions, key=lambda r: natural_sort_key(r.label))):
        if revision.sequence != rank:
            revision.sequence = rank


def run_import(db: Session, root: Path | None = None) -> ImportReport:
    root = root or DATA_ROOT
    report = ImportReport(data_root=str(root))

    for orphan in orphan_csv_files(root):
        report.files_scanned += 1
        report.errors.append(
            ImportError_(
                path=str(orphan),
                message=(
                    "CSV found directly under the data root with no revision folder; "
                    "expected <root>/<revision>/<component>.csv or "
                    "<root>/<project>/<revision>/<component>.csv"
                ),
            )
        )

    discovered = discover_csv_files(root)
    touched_components: set[int] = set()

    for item in discovered:
        report.files_scanned += 1
        try:
            file_hash = _hash_file(item.path)
            mtime = item.path.stat().st_mtime
        except OSError as exc:
            report.errors.append(ImportError_(path=str(item.path), message=f"Could not read file: {exc}"))
            continue

        project_dir = item.path.parent.parent  # see discovery.discover_csv_files
        project = _get_or_create_project(db, item.project_name, project_dir)
        component = _get_or_create_component(db, project, item.component_name)
        touched_components.add(component.id)

        existing = (
            db.query(models.Revision)
            .filter(
                models.Revision.component_id == component.id,
                models.Revision.label == item.revision_label,
            )
            .one_or_none()
        )

        if existing is not None and existing.file_hash == file_hash:
            report.unchanged += 1
            continue

        try:
            parsed = parse_results_csv(item.path)
        except CsvValidationError as exc:
            report.errors.append(ImportError_(path=str(item.path), message=str(exc)))
            continue

        assessment = assess_samples(parsed.samples)

        if existing is None:
            revision = models.Revision(
                component_id=component.id,
                label=item.revision_label,
                sequence=0,  # fixed up by _resequence_revisions below
                source_path=str(item.path),
                file_hash=file_hash,
                file_mtime=mtime,
            )
            db.add(revision)
            db.flush()
            report.imported += 1
        else:
            revision = existing
            db.query(models.Sample).filter(models.Sample.revision_id == revision.id).delete()
            revision.source_path = str(item.path)
            revision.file_hash = file_hash
            revision.file_mtime = mtime
            report.updated += 1

        revision.row_count = assessment.sample_count
        revision.overall_max_magnitude = assessment.overall_max_magnitude
        revision.overall_max_frequency = assessment.overall_max_frequency
        revision.assessed_max_magnitude = assessment.assessed_max_magnitude
        revision.assessed_peak_frequency = assessment.assessed_peak_frequency
        revision.passes_limit = assessment.passes_limit

        db.add_all(
            models.Sample(revision_id=revision.id, frequency_hz=f, magnitude_mm=m)
            for f, m in parsed.samples
        )

    for component_id in touched_components:
        component = db.get(models.Component, component_id)
        if component:
            _resequence_revisions(db, component)

    db.commit()
    return report


def persist_report(db: Session, report: ImportReport) -> models.ImportRun:
    import datetime

    run = models.ImportRun(
        data_root=report.data_root,
        finished_at=datetime.datetime.now(datetime.timezone.utc),
        files_scanned=report.files_scanned,
        imported_count=report.imported,
        updated_count=report.updated,
        unchanged_count=report.unchanged,
        error_count=len(report.errors),
        errors=[{"path": e.path, "message": e.message} for e in report.errors],
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run

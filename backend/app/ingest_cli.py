"""Manual ingestion trigger: ``python -m app.ingest_cli``.

Useful for cron/scheduled-task based syncing, independent of the API server.
Exits non-zero if any file failed to import, so it can be used as a CI/cron
health check.
"""
from __future__ import annotations

import sys

from .database import SessionLocal, init_db
from .ingestion.importer import persist_report, run_import


def main() -> int:
    init_db()
    db = SessionLocal()
    try:
        report = run_import(db)
        persist_report(db, report)
    finally:
        db.close()

    print(
        f"Scanned {report.files_scanned} file(s): "
        f"{report.imported} imported, {report.updated} updated, "
        f"{report.unchanged} unchanged, {len(report.errors)} error(s)."
    )
    for err in report.errors:
        print(f"  ERROR  {err.path}: {err.message}")
    return 1 if report.errors else 0


if __name__ == "__main__":
    sys.exit(main())

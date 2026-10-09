"""Application configuration.

Values are read from environment variables so the service can be pointed at
different data/DB locations in different environments without code changes.
"""
from __future__ import annotations

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent

# Root directory that the ingestion process scans for revision data.
DATA_ROOT = Path(os.environ.get("SIM_DATA_ROOT", BACKEND_DIR / "data" / "raw")).resolve()

# SQLite database file.
DATABASE_URL = os.environ.get(
    "SIM_DATABASE_URL",
    f"sqlite:///{(BACKEND_DIR / 'data' / 'app.db').as_posix()}",
)

# Engineering review rule (kept centralized so it is visible/auditable and
# easy to change if the review criterion changes).
ASSESSMENT_FREQ_MIN_HZ = 0.0
ASSESSMENT_FREQ_MAX_HZ = 50.0
ASSESSMENT_LIMIT_MM = 15.0

# Name used for the single project when the scanned data root does not have
# an extra project-folder level (see ingestion/discovery.py).
DEFAULT_PROJECT_NAME = os.environ.get("SIM_DEFAULT_PROJECT_NAME", "Default Project")

RUN_INGEST_ON_STARTUP = os.environ.get("SIM_INGEST_ON_STARTUP", "1") != "0"

CORS_ORIGINS = os.environ.get(
    "SIM_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
).split(",")

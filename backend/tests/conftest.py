from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Must be set before `app.config` is imported anywhere (including transitively
# via `app.main` in the `client` fixture) so the test server never re-ingests
# the real CSV data root into the real on-disk database.
os.environ["SIM_INGEST_ON_STARTUP"] = "0"

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base


@pytest.fixture()
def db_session():
    # StaticPool keeps a single shared connection alive for the whole engine,
    # which is required for an in-memory SQLite DB to be visible across the
    # separate thread the TestClient's app runs requests on.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def client(db_session):
    from fastapi.testclient import TestClient

    from app.database import get_db
    from app.main import app

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def write_csv(path: Path, rows: list[tuple[float, float]], header: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    if header:
        lines.append("Frequency [Hz],Magnitude [mm]")
    lines.extend(f"{f},{m}" for f, m in rows)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

from __future__ import annotations

import datetime
import enum

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    # Directory this project was discovered under, so optional per-component
    # reference images (<source_dir>/<Component>.png) can be located later.
    source_dir: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    components: Mapped[list["Component"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="Component.name"
    )


class Component(Base):
    __tablename__ = "components"
    __table_args__ = (UniqueConstraint("project_id", "name", name="uq_component_project_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    project: Mapped["Project"] = relationship(back_populates="components")
    revisions: Mapped[list["Revision"]] = relationship(
        back_populates="component", cascade="all, delete-orphan", order_by="Revision.sequence"
    )
    demands: Mapped[list["Demand"]] = relationship(
        back_populates="component", cascade="all, delete-orphan"
    )


class Revision(Base):
    """One imported CSV file: the result set for a single component at a single revision."""

    __tablename__ = "revisions"
    __table_args__ = (UniqueConstraint("component_id", "label", name="uq_revision_component_label"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    component_id: Mapped[int] = mapped_column(ForeignKey("components.id", ondelete="CASCADE"))
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    # Monotonic import/discovery order used to sort revisions chronologically
    # regardless of how the label happens to be named.
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)

    source_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    file_mtime: Mapped[float] = mapped_column(Float, nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # --- Cached summary, computed at ingestion time from the stored samples ---
    overall_max_magnitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    overall_max_frequency: Mapped[float | None] = mapped_column(Float, nullable=True)
    assessed_max_magnitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    assessed_peak_frequency: Mapped[float | None] = mapped_column(Float, nullable=True)
    passes_limit: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    imported_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    component: Mapped["Component"] = relationship(back_populates="revisions")
    samples: Mapped[list["Sample"]] = relationship(
        back_populates="revision", cascade="all, delete-orphan", order_by="Sample.frequency_hz"
    )
    demands: Mapped[list["Demand"]] = relationship(back_populates="origin_revision")


class Sample(Base):
    __tablename__ = "samples"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    revision_id: Mapped[int] = mapped_column(ForeignKey("revisions.id", ondelete="CASCADE"), index=True)
    frequency_hz: Mapped[float] = mapped_column(Float, nullable=False)
    magnitude_mm: Mapped[float] = mapped_column(Float, nullable=False)

    revision: Mapped["Revision"] = relationship(back_populates="samples")


class DemandStatus(str, enum.Enum):
    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    RESOLVED = "Resolved"


class Demand(Base):
    __tablename__ = "demands"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    component_id: Mapped[int] = mapped_column(ForeignKey("components.id", ondelete="CASCADE"))
    description: Mapped[str] = mapped_column(String(2000), nullable=False)
    status: Mapped[DemandStatus] = mapped_column(
        Enum(DemandStatus), nullable=False, default=DemandStatus.OPEN
    )
    is_manual: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Origin finding snapshot: the specific revision/metric/value that triggered
    # this demand, frozen at creation time so later re-imports of the same
    # revision label cannot silently rewrite history.
    origin_revision_id: Mapped[int | None] = mapped_column(
        ForeignKey("revisions.id", ondelete="SET NULL"), nullable=True
    )
    origin_metric: Mapped[str | None] = mapped_column(String(100), nullable=True)
    origin_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    origin_frequency: Mapped[float | None] = mapped_column(Float, nullable=True)
    origin_limit: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    component: Mapped["Component"] = relationship(back_populates="demands")
    origin_revision: Mapped["Revision | None"] = relationship(back_populates="demands")


class ImportRun(Base):
    """Audit log of each ingestion/sync pass, including files that failed to import."""

    __tablename__ = "import_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    started_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    finished_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    data_root: Mapped[str] = mapped_column(String(1000), nullable=False)

    files_scanned: Mapped[int] = mapped_column(Integer, default=0)
    imported_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_count: Mapped[int] = mapped_column(Integer, default=0)
    unchanged_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)

    # List of {"path": str, "message": str} for files that could not be imported.
    errors: Mapped[list] = mapped_column(JSON, default=list)

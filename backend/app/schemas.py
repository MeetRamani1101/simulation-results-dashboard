from __future__ import annotations

import datetime

from pydantic import BaseModel, ConfigDict, Field

from .models import DemandStatus


class AssessmentOut(BaseModel):
    limit_mm: float
    freq_min_hz: float
    freq_max_hz: float
    assessed_max_magnitude: float | None
    assessed_peak_frequency: float | None
    overall_max_magnitude: float | None
    overall_max_frequency: float | None
    passes_limit: bool | None


class SampleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    frequency_hz: float
    magnitude_mm: float


class RevisionSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    label: str
    sequence: int
    row_count: int
    imported_at: datetime.datetime
    updated_at: datetime.datetime
    assessment: AssessmentOut


class RevisionDetailOut(RevisionSummaryOut):
    component_id: int
    component_name: str
    project_id: int
    project_name: str
    samples: list[SampleOut]


class ComponentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    project_id: int
    revision_count: int
    latest_revision: RevisionSummaryOut | None = None
    has_image: bool = False


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    component_count: int


class ProjectDetailOut(ProjectOut):
    components: list[ComponentOut]


class RevisionCompareOut(BaseModel):
    revision_id: int
    label: str
    sequence: int
    assessment: AssessmentOut
    samples: list[SampleOut]
    delta_assessed_max_magnitude: float | None = Field(
        default=None, description="Change vs the previous revision in sequence order"
    )


class ComponentCompareOut(BaseModel):
    component_id: int
    component_name: str
    project_id: int
    project_name: str
    limit_mm: float
    freq_min_hz: float
    freq_max_hz: float
    revisions: list[RevisionCompareOut]


# ---- Demands ----


class DemandCreate(BaseModel):
    component_id: int
    description: str = Field(min_length=1, max_length=2000)
    origin_revision_id: int | None = None
    status: DemandStatus = DemandStatus.OPEN


class DemandUpdate(BaseModel):
    description: str | None = Field(default=None, min_length=1, max_length=2000)
    status: DemandStatus | None = None


class DemandRevisionResultOut(BaseModel):
    revision_id: int
    label: str
    sequence: int
    assessment: AssessmentOut
    is_origin: bool


class DemandOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    component_id: int
    component_name: str
    project_id: int
    project_name: str
    description: str
    status: DemandStatus
    is_manual: bool
    origin_revision_id: int | None
    origin_revision_label: str | None
    origin_metric: str | None
    origin_value: float | None
    origin_frequency: float | None
    origin_limit: float | None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    latest_revision_id: int | None
    latest_revision_label: str | None
    latest_passes_limit: bool | None


class DemandDetailOut(DemandOut):
    revision_results: list[DemandRevisionResultOut]


# ---- Ingestion ----


class ImportErrorOut(BaseModel):
    path: str
    message: str


class ImportRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    started_at: datetime.datetime
    finished_at: datetime.datetime | None
    data_root: str
    files_scanned: int
    imported_count: int
    updated_count: int
    unchanged_count: int
    error_count: int
    errors: list[ImportErrorOut]

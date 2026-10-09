"""Read-model helpers: turn ORM rows into API schema objects.

Kept separate from the routers so response-shaping logic is unit-testable
and reusable (e.g. the same revision-summary shape is used in the component
list, the revision detail, and the comparison endpoint).
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from . import models, schemas


def revision_assessment(revision: models.Revision) -> schemas.AssessmentOut:
    from .config import ASSESSMENT_FREQ_MAX_HZ, ASSESSMENT_FREQ_MIN_HZ, ASSESSMENT_LIMIT_MM

    return schemas.AssessmentOut(
        limit_mm=ASSESSMENT_LIMIT_MM,
        freq_min_hz=ASSESSMENT_FREQ_MIN_HZ,
        freq_max_hz=ASSESSMENT_FREQ_MAX_HZ,
        assessed_max_magnitude=revision.assessed_max_magnitude,
        assessed_peak_frequency=revision.assessed_peak_frequency,
        overall_max_magnitude=revision.overall_max_magnitude,
        overall_max_frequency=revision.overall_max_frequency,
        passes_limit=revision.passes_limit,
    )


def revision_summary(revision: models.Revision) -> schemas.RevisionSummaryOut:
    return schemas.RevisionSummaryOut(
        id=revision.id,
        label=revision.label,
        sequence=revision.sequence,
        row_count=revision.row_count,
        imported_at=revision.imported_at,
        updated_at=revision.updated_at,
        assessment=revision_assessment(revision),
    )


def revision_detail(revision: models.Revision) -> schemas.RevisionDetailOut:
    base = revision_summary(revision)
    component = revision.component
    return schemas.RevisionDetailOut(
        **base.model_dump(),
        component_id=component.id,
        component_name=component.name,
        project_id=component.project_id,
        project_name=component.project.name,
        samples=[schemas.SampleOut.model_validate(s) for s in revision.samples],
    )


def component_out(component: models.Component) -> schemas.ComponentOut:
    from pathlib import Path

    from .ingestion.discovery import find_component_image

    revisions = sorted(component.revisions, key=lambda r: r.sequence)
    latest = revisions[-1] if revisions else None
    project_dir = Path(component.project.source_dir) if component.project.source_dir else None
    has_image = bool(project_dir and find_component_image(project_dir, component.name))
    return schemas.ComponentOut(
        id=component.id,
        name=component.name,
        project_id=component.project_id,
        revision_count=len(revisions),
        latest_revision=revision_summary(latest) if latest else None,
        has_image=has_image,
    )


def project_detail(project: models.Project) -> schemas.ProjectDetailOut:
    return schemas.ProjectDetailOut(
        id=project.id,
        name=project.name,
        component_count=len(project.components),
        components=[component_out(c) for c in project.components],
    )


def project_out(project: models.Project) -> schemas.ProjectOut:
    return schemas.ProjectOut(id=project.id, name=project.name, component_count=len(project.components))


def component_compare(component: models.Component, revisions: list[models.Revision]) -> schemas.ComponentCompareOut:
    from .config import ASSESSMENT_FREQ_MAX_HZ, ASSESSMENT_FREQ_MIN_HZ, ASSESSMENT_LIMIT_MM

    ordered = sorted(revisions, key=lambda r: r.sequence)
    out_revisions: list[schemas.RevisionCompareOut] = []
    prev_max: float | None = None
    for revision in ordered:
        assessment = revision_assessment(revision)
        delta = None
        if prev_max is not None and assessment.assessed_max_magnitude is not None:
            delta = round(assessment.assessed_max_magnitude - prev_max, 6)
        out_revisions.append(
            schemas.RevisionCompareOut(
                revision_id=revision.id,
                label=revision.label,
                sequence=revision.sequence,
                assessment=assessment,
                samples=[schemas.SampleOut.model_validate(s) for s in revision.samples],
                delta_assessed_max_magnitude=delta,
            )
        )
        if assessment.assessed_max_magnitude is not None:
            prev_max = assessment.assessed_max_magnitude

    return schemas.ComponentCompareOut(
        component_id=component.id,
        component_name=component.name,
        project_id=component.project_id,
        project_name=component.project.name,
        limit_mm=ASSESSMENT_LIMIT_MM,
        freq_min_hz=ASSESSMENT_FREQ_MIN_HZ,
        freq_max_hz=ASSESSMENT_FREQ_MAX_HZ,
        revisions=out_revisions,
    )


def demand_out(demand: models.Demand) -> schemas.DemandOut:
    component = demand.component
    revisions = sorted(component.revisions, key=lambda r: r.sequence)
    latest = revisions[-1] if revisions else None
    return schemas.DemandOut(
        id=demand.id,
        component_id=component.id,
        component_name=component.name,
        project_id=component.project_id,
        project_name=component.project.name,
        description=demand.description,
        status=demand.status,
        is_manual=demand.is_manual,
        origin_revision_id=demand.origin_revision_id,
        origin_revision_label=demand.origin_revision.label if demand.origin_revision else None,
        origin_metric=demand.origin_metric,
        origin_value=demand.origin_value,
        origin_frequency=demand.origin_frequency,
        origin_limit=demand.origin_limit,
        created_at=demand.created_at,
        updated_at=demand.updated_at,
        latest_revision_id=latest.id if latest else None,
        latest_revision_label=latest.label if latest else None,
        latest_passes_limit=latest.passes_limit if latest else None,
    )


def demand_detail(demand: models.Demand) -> schemas.DemandDetailOut:
    base = demand_out(demand)
    component = demand.component
    revisions = sorted(component.revisions, key=lambda r: r.sequence)
    results = [
        schemas.DemandRevisionResultOut(
            revision_id=r.id,
            label=r.label,
            sequence=r.sequence,
            assessment=revision_assessment(r),
            is_origin=(r.id == demand.origin_revision_id),
        )
        for r in revisions
    ]
    return schemas.DemandDetailOut(**base.model_dump(), revision_results=results)

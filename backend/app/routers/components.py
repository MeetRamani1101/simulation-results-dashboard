from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..database import get_db
from ..ingestion.discovery import find_component_image

router = APIRouter(prefix="/api/components", tags=["components"])


@router.get("/{component_id}", response_model=schemas.ComponentOut)
def get_component(component_id: int, db: Session = Depends(get_db)):
    component = db.get(models.Component, component_id)
    if component is None:
        raise HTTPException(status_code=404, detail="Component not found")
    return crud.component_out(component)


@router.get("/{component_id}/image")
def get_component_image(component_id: int, db: Session = Depends(get_db)):
    """Optional reference photo for the physical component (e.g.
    <project_dir>/Bracket.png next to the revision folders), if one was
    present in the ingested data. 404 if none exists - the frontend treats
    that as "no photo available", not an error."""
    component = db.get(models.Component, component_id)
    if component is None:
        raise HTTPException(status_code=404, detail="Component not found")
    project_dir = component.project.source_dir
    image_path = find_component_image(Path(project_dir), component.name) if project_dir else None
    if image_path is None:
        raise HTTPException(status_code=404, detail="No reference image available for this component")
    return FileResponse(image_path)


@router.get("/{component_id}/revisions", response_model=list[schemas.RevisionSummaryOut])
def list_revisions(component_id: int, db: Session = Depends(get_db)):
    component = db.get(models.Component, component_id)
    if component is None:
        raise HTTPException(status_code=404, detail="Component not found")
    revisions = sorted(component.revisions, key=lambda r: r.sequence)
    return [crud.revision_summary(r) for r in revisions]


@router.get("/{component_id}/compare", response_model=schemas.ComponentCompareOut)
def compare_revisions(
    component_id: int,
    revision_ids: str | None = Query(
        default=None,
        description="Comma-separated revision ids to compare. Defaults to all revisions of the component.",
    ),
    db: Session = Depends(get_db),
):
    component = db.get(models.Component, component_id)
    if component is None:
        raise HTTPException(status_code=404, detail="Component not found")

    if revision_ids:
        try:
            ids = {int(x) for x in revision_ids.split(",") if x.strip()}
        except ValueError:
            raise HTTPException(status_code=400, detail="revision_ids must be a comma-separated list of integers")
        revisions = [r for r in component.revisions if r.id in ids]
        missing = ids - {r.id for r in revisions}
        if missing:
            raise HTTPException(
                status_code=404,
                detail=f"Revision id(s) not found on this component: {sorted(missing)}",
            )
    else:
        revisions = list(component.revisions)

    if not revisions:
        raise HTTPException(status_code=404, detail="No revisions available to compare")

    return crud.component_compare(component, revisions)

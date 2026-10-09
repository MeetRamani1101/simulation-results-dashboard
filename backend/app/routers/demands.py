from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/demands", tags=["demands"])


@router.get("", response_model=list[schemas.DemandOut])
def list_demands(
    status: models.DemandStatus | None = Query(default=None),
    project_id: int | None = Query(default=None),
    component_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    q = db.query(models.Demand)
    if status is not None:
        q = q.filter(models.Demand.status == status)
    if component_id is not None:
        q = q.filter(models.Demand.component_id == component_id)
    if project_id is not None:
        q = q.join(models.Component).filter(models.Component.project_id == project_id)
    demands = q.order_by(models.Demand.created_at.desc()).all()
    return [crud.demand_out(d) for d in demands]


@router.post("", response_model=schemas.DemandDetailOut, status_code=201)
def create_demand(payload: schemas.DemandCreate, db: Session = Depends(get_db)):
    component = db.get(models.Component, payload.component_id)
    if component is None:
        raise HTTPException(status_code=404, detail="Component not found")

    demand = models.Demand(
        component_id=component.id,
        description=payload.description,
        status=payload.status,
    )

    if payload.origin_revision_id is not None:
        revision = db.get(models.Revision, payload.origin_revision_id)
        if revision is None or revision.component_id != component.id:
            raise HTTPException(
                status_code=404, detail="origin_revision_id must be a revision of the given component"
            )
        demand.is_manual = False
        demand.origin_revision_id = revision.id
        demand.origin_metric = f"max_magnitude_0_50hz"
        demand.origin_value = revision.assessed_max_magnitude
        demand.origin_frequency = revision.assessed_peak_frequency
        from ..config import ASSESSMENT_LIMIT_MM

        demand.origin_limit = ASSESSMENT_LIMIT_MM
    else:
        demand.is_manual = True

    db.add(demand)
    db.commit()
    db.refresh(demand)
    return crud.demand_detail(demand)


@router.get("/{demand_id}", response_model=schemas.DemandDetailOut)
def get_demand(demand_id: int, db: Session = Depends(get_db)):
    demand = db.get(models.Demand, demand_id)
    if demand is None:
        raise HTTPException(status_code=404, detail="Demand not found")
    return crud.demand_detail(demand)


@router.patch("/{demand_id}", response_model=schemas.DemandDetailOut)
def update_demand(demand_id: int, payload: schemas.DemandUpdate, db: Session = Depends(get_db)):
    demand = db.get(models.Demand, demand_id)
    if demand is None:
        raise HTTPException(status_code=404, detail="Demand not found")

    if payload.description is not None:
        demand.description = payload.description
    if payload.status is not None:
        demand.status = payload.status

    db.commit()
    db.refresh(demand)
    return crud.demand_detail(demand)

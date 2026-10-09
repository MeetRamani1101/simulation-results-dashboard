from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/revisions", tags=["revisions"])


@router.get("/{revision_id}", response_model=schemas.RevisionDetailOut)
def get_revision(revision_id: int, db: Session = Depends(get_db)):
    revision = db.get(models.Revision, revision_id)
    if revision is None:
        raise HTTPException(status_code=404, detail="Revision not found")
    return crud.revision_detail(revision)

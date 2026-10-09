"""Optional convenience script: creates one example demand per component,
originating from each component's first revision, if it does not already
exist. Demonstrates the "track a finding across revisions" workflow described
in the spec. Not required for the app to function - an engineer can create
the same demands from the UI by clicking "Create demand" on a failed finding.

Usage: python -m app.seed_cli
"""
from __future__ import annotations

from . import models
from .database import SessionLocal, init_db


DEMAND_TEMPLATES = {
    "Bracket": "Exceeds the 15 mm limit near its resonant peak in rev1; investigate stiffness/damping of the mounting rib structure.",
    "Housing": "Exceeds the 15 mm limit near its resonant peak in rev1; review wall thickness around the resonant mode.",
    "Lens": "Exceeds the 15 mm limit near its resonant peak in rev1; evaluate rib/boss layout to shift or damp the resonant peak.",
}


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        components = db.query(models.Component).all()
        for component in components:
            template = DEMAND_TEMPLATES.get(component.name)
            if template is None:
                continue
            first_revision = min(component.revisions, key=lambda r: r.sequence, default=None)
            if first_revision is None or first_revision.passes_limit is not False:
                continue  # only seed from a genuinely failing first revision

            already_exists = (
                db.query(models.Demand)
                .filter(
                    models.Demand.component_id == component.id,
                    models.Demand.origin_revision_id == first_revision.id,
                )
                .first()
            )
            if already_exists:
                print(f"Skipping {component.name}: demand already exists for {first_revision.label}")
                continue

            demand = models.Demand(
                component_id=component.id,
                description=f"{component.name} {template}",
                is_manual=False,
                origin_revision_id=first_revision.id,
                origin_metric="max_magnitude_0_50hz",
                origin_value=first_revision.assessed_max_magnitude,
                origin_frequency=first_revision.assessed_peak_frequency,
                origin_limit=15.0,
            )
            db.add(demand)
            db.commit()
            print(f"Created demand for {component.name} from {first_revision.label}")
    finally:
        db.close()


if __name__ == "__main__":
    main()

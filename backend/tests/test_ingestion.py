from __future__ import annotations

from pathlib import Path

from app import models
from app.ingestion.importer import run_import
from tests.conftest import write_csv


def _make_tree(root: Path) -> None:
    write_csv(root / "rev1" / "Bracket.csv", [(5.0, 2.1), (37.6, 19.9), (48.3, 1.6)])
    write_csv(root / "rev1" / "Housing.csv", [(5.0, 1.5), (37.6, 16.7)])
    write_csv(root / "rev2" / "Bracket.csv", [(5.0, 2.1), (37.8, 22.0), (48.3, 2.0)])
    write_csv(root / "rev2" / "Housing.csv", [(5.0, 1.4), (37.8, 14.9)])


def test_import_creates_project_component_revision_sample(db_session, tmp_path):
    _make_tree(tmp_path)
    report = run_import(db_session, root=tmp_path)

    assert report.files_scanned == 4
    assert report.imported == 4
    assert report.errors == []

    projects = db_session.query(models.Project).all()
    assert len(projects) == 1
    assert projects[0].name == "Default Project"

    components = {c.name for c in projects[0].components}
    assert components == {"Bracket", "Housing"}

    bracket = next(c for c in projects[0].components if c.name == "Bracket")
    assert {r.label for r in bracket.revisions} == {"rev1", "rev2"}
    rev1 = next(r for r in bracket.revisions if r.label == "rev1")
    assert rev1.row_count == 3
    assert rev1.assessed_max_magnitude == 19.9
    assert rev1.assessed_peak_frequency == 37.6
    assert rev1.passes_limit is False

    sample_count = db_session.query(models.Sample).filter(models.Sample.revision_id == rev1.id).count()
    assert sample_count == 3


def test_reimport_unchanged_file_is_idempotent(db_session, tmp_path):
    _make_tree(tmp_path)
    run_import(db_session, root=tmp_path)
    report2 = run_import(db_session, root=tmp_path)

    assert report2.imported == 0
    assert report2.updated == 0
    assert report2.unchanged == 4
    assert db_session.query(models.Revision).count() == 4
    assert db_session.query(models.Sample).count() == 10  # 3+2+3+2 rows, no duplicates


def test_changed_file_updates_samples_without_duplicating_revision(db_session, tmp_path):
    _make_tree(tmp_path)
    run_import(db_session, root=tmp_path)

    # Overwrite rev1/Bracket.csv with new data (file content changes -> hash changes)
    write_csv(tmp_path / "rev1" / "Bracket.csv", [(5.0, 2.1), (37.6, 10.0)])
    report2 = run_import(db_session, root=tmp_path)

    assert report2.updated == 1
    assert report2.unchanged == 3

    bracket = db_session.query(models.Component).filter(models.Component.name == "Bracket").one()
    assert len(bracket.revisions) == 2  # still just rev1 + rev2, not a duplicate
    rev1 = next(r for r in bracket.revisions if r.label == "rev1")
    assert rev1.assessed_max_magnitude == 10.0
    assert rev1.passes_limit is True
    assert rev1.row_count == 2


def test_malformed_file_is_reported_and_does_not_block_others(db_session, tmp_path):
    _make_tree(tmp_path)
    (tmp_path / "rev1" / "Lens.csv").write_text(
        "Frequency [Hz],Magnitude [mm]\n5.0,not-a-number\n", encoding="utf-8"
    )

    report = run_import(db_session, root=tmp_path)

    assert report.imported == 4  # the 4 good files still import
    assert len(report.errors) == 1
    assert "Lens.csv" in report.errors[0].path

    # The component may be registered (its name was discovered on disk), but
    # no corrupt/partial revision was created from the failed file.
    lens = db_session.query(models.Component).filter(models.Component.name == "Lens").one_or_none()
    if lens is not None:
        assert lens.revisions == []


def test_revision_sequence_orders_naturally(db_session, tmp_path):
    write_csv(tmp_path / "rev1" / "Bracket.csv", [(5.0, 1.0)])
    write_csv(tmp_path / "rev2" / "Bracket.csv", [(5.0, 1.0)])
    write_csv(tmp_path / "rev10" / "Bracket.csv", [(5.0, 1.0)])
    run_import(db_session, root=tmp_path)

    bracket = db_session.query(models.Component).filter(models.Component.name == "Bracket").one()
    ordered_labels = [r.label for r in sorted(bracket.revisions, key=lambda r: r.sequence)]
    assert ordered_labels == ["rev1", "rev2", "rev10"]


def test_explicit_project_folder_layout(db_session, tmp_path):
    write_csv(tmp_path / "Headlamp" / "rev1" / "Bracket.csv", [(5.0, 1.0)])
    run_import(db_session, root=tmp_path)

    project = db_session.query(models.Project).one()
    assert project.name == "Headlamp"


def test_orphan_csv_at_root_is_reported(db_session, tmp_path):
    (tmp_path / "Loose.csv").write_text("Frequency [Hz],Magnitude [mm]\n5.0,1.0\n", encoding="utf-8")
    report = run_import(db_session, root=tmp_path)
    assert len(report.errors) == 1
    assert "Loose.csv" in report.errors[0].path

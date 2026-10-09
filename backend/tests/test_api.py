from __future__ import annotations

from app.ingestion.importer import run_import
from tests.conftest import write_csv


def _seed(db_session, tmp_path):
    write_csv(tmp_path / "rev1" / "Bracket.csv", [(5.0, 2.1), (37.6, 19.9), (48.3, 1.6)])
    write_csv(tmp_path / "rev2" / "Bracket.csv", [(5.0, 2.1), (37.8, 22.0), (48.3, 2.0)])
    write_csv(tmp_path / "rev3" / "Bracket.csv", [(5.0, 2.0), (37.8, 13.8), (48.3, 1.8)])
    run_import(db_session, root=tmp_path)


def test_list_projects_and_components(client, db_session, tmp_path):
    _seed(db_session, tmp_path)

    resp = client.get("/api/projects")
    assert resp.status_code == 200
    projects = resp.json()
    assert len(projects) == 1
    assert projects[0]["component_count"] == 1

    project_id = projects[0]["id"]
    resp = client.get(f"/api/projects/{project_id}")
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["components"][0]["name"] == "Bracket"
    assert detail["components"][0]["latest_revision"]["label"] == "rev3"
    assert detail["components"][0]["latest_revision"]["assessment"]["passes_limit"] is True


def test_revision_detail_includes_samples_and_assessment(client, db_session, tmp_path):
    _seed(db_session, tmp_path)
    project_id = client.get("/api/projects").json()[0]["id"]
    component = client.get(f"/api/projects/{project_id}").json()["components"][0]
    latest_revision_id = component["latest_revision"]["id"]

    resp = client.get(f"/api/revisions/{latest_revision_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert "samples" in body and len(body["samples"]) == 3
    assert body["assessment"]["limit_mm"] == 15.0
    assert body["assessment"]["freq_max_hz"] == 50.0


def test_compare_endpoint_shows_deltas(client, db_session, tmp_path):
    _seed(db_session, tmp_path)
    project_id = client.get("/api/projects").json()[0]["id"]
    component_id = client.get(f"/api/projects/{project_id}").json()["components"][0]["id"]

    resp = client.get(f"/api/components/{component_id}/compare")
    assert resp.status_code == 200
    body = resp.json()
    labels = [r["label"] for r in body["revisions"]]
    assert labels == ["rev1", "rev2", "rev3"]
    assert body["revisions"][0]["delta_assessed_max_magnitude"] is None
    assert body["revisions"][1]["delta_assessed_max_magnitude"] == 2.1  # 22.0 - 19.9
    assert [r["assessment"]["passes_limit"] for r in body["revisions"]] == [False, False, True]


def test_revision_not_found_returns_404(client, db_session):
    resp = client.get("/api/revisions/9999")
    assert resp.status_code == 404


def test_create_demand_from_failed_finding_and_update_status(client, db_session, tmp_path):
    _seed(db_session, tmp_path)
    project_id = client.get("/api/projects").json()[0]["id"]
    component = client.get(f"/api/projects/{project_id}").json()["components"][0]
    component_id = component["id"]

    revisions = client.get(f"/api/components/{component_id}/revisions").json()
    rev1 = next(r for r in revisions if r["label"] == "rev1")

    resp = client.post(
        "/api/demands",
        json={
            "component_id": component_id,
            "description": "Investigate Bracket resonance near 37.6 Hz",
            "origin_revision_id": rev1["id"],
        },
    )
    assert resp.status_code == 201
    demand = resp.json()
    assert demand["is_manual"] is False
    assert demand["origin_value"] == 19.9
    assert demand["origin_frequency"] == 37.6
    assert demand["origin_limit"] == 15.0
    assert demand["status"] == "Open"
    # Latest observed result reflects rev3 (passing) even though origin is rev1 (failing)
    assert demand["latest_revision_label"] == "rev3"
    assert demand["latest_passes_limit"] is True
    # revision_results trace the finding across all revisions
    results = {r["label"]: r["assessment"]["passes_limit"] for r in demand["revision_results"]}
    assert results == {"rev1": False, "rev2": False, "rev3": True}

    demand_id = demand["id"]
    resp = client.patch(f"/api/demands/{demand_id}", json={"status": "In Progress"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "In Progress"

    # A later passing result must NOT auto-resolve the demand.
    assert resp.json()["status"] != "Resolved"

    resp = client.get("/api/demands", params={"status": "In Progress"})
    assert len(resp.json()) == 1


def test_create_manual_demand(client, db_session, tmp_path):
    _seed(db_session, tmp_path)
    project_id = client.get("/api/projects").json()[0]["id"]
    component_id = client.get(f"/api/projects/{project_id}").json()["components"][0]["id"]

    resp = client.post(
        "/api/demands",
        json={"component_id": component_id, "description": "Review mounting stiffness"},
    )
    assert resp.status_code == 201
    demand = resp.json()
    assert demand["is_manual"] is True
    assert demand["origin_revision_id"] is None


def test_demand_for_unknown_component_404s(client, db_session):
    resp = client.post("/api/demands", json={"component_id": 999, "description": "x"})
    assert resp.status_code == 404


def test_ingest_run_endpoint(client, db_session, tmp_path, monkeypatch):
    import app.routers.ingest as ingest_module

    write_csv(tmp_path / "rev1" / "Bracket.csv", [(5.0, 1.0)])
    monkeypatch.setattr(ingest_module, "DATA_ROOT", tmp_path, raising=False)

    def fake_run_import(db, root=None):
        from app.ingestion.importer import run_import as real_run_import

        return real_run_import(db, root=tmp_path)

    monkeypatch.setattr(ingest_module, "run_import", fake_run_import)

    resp = client.post("/api/ingest/run")
    assert resp.status_code == 200
    body = resp.json()
    assert body["imported_count"] == 1
    assert body["error_count"] == 0

    resp = client.get("/api/ingest/runs/latest")
    assert resp.status_code == 200
    assert resp.json()["imported_count"] == 1


def test_component_image_present_and_absent(client, db_session, tmp_path):
    _seed(db_session, tmp_path)
    # Bracket has a reference photo sitting next to the revision folders;
    # Housing (never ingested here) does not exist at all.
    (tmp_path / "Bracket.png").write_bytes(b"\x89PNG\r\n\x1a\nfake-image-bytes")

    project_id = client.get("/api/projects").json()[0]["id"]
    components = client.get(f"/api/projects/{project_id}").json()["components"]
    bracket = next(c for c in components if c["name"] == "Bracket")
    assert bracket["has_image"] is True

    resp = client.get(f"/api/components/{bracket['id']}/image")
    assert resp.status_code == 200
    assert resp.content == b"\x89PNG\r\n\x1a\nfake-image-bytes"


def test_component_image_404_when_missing(client, db_session, tmp_path):
    _seed(db_session, tmp_path)
    project_id = client.get("/api/projects").json()[0]["id"]
    bracket = client.get(f"/api/projects/{project_id}").json()["components"][0]
    assert bracket["has_image"] is False

    resp = client.get(f"/api/components/{bracket['id']}/image")
    assert resp.status_code == 404


def test_component_image_404_for_unknown_component(client, db_session):
    resp = client.get("/api/components/9999/image")
    assert resp.status_code == 404

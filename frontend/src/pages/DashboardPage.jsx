import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import { PassFailBadge } from "../components/Badges";
import ComponentImage from "../components/ComponentImage";

export default function DashboardPage() {
  const [projects, setProjects] = useState(null);
  const [projectDetail, setProjectDetail] = useState(null);
  const [error, setError] = useState(null);
  const [searchParams, setSearchParams] = useSearchParams();

  const selectedProjectId = searchParams.get("project");

  useEffect(() => {
    api
      .listProjects()
      .then((list) => {
        setProjects(list);
        if (!selectedProjectId && list.length > 0) {
          setSearchParams({ project: String(list[0].id) }, { replace: true });
        }
      })
      .catch((err) => setError(err.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!selectedProjectId) return;
    api
      .getProject(selectedProjectId)
      .then(setProjectDetail)
      .catch((err) => setError(err.message));
  }, [selectedProjectId]);

  if (error) return <div className="banner banner-error">{error}</div>;
  if (!projects) return <div className="loading">Loading projects…</div>;

  if (projects.length === 0) {
    return (
      <div className="empty-state card">
        No projects found yet. Click <strong>Sync data</strong> in the sidebar to import simulation
        CSVs from the configured data root.
      </div>
    );
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h2>Projects</h2>
          <p className="muted" style={{ marginTop: 0 }}>
            Select a project to review its components and revisions.
          </p>
        </div>
        {projects.length > 1 && (
          <select
            value={selectedProjectId || ""}
            onChange={(e) => setSearchParams({ project: e.target.value })}
          >
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        )}
      </div>

      {!projectDetail ? (
        <div className="loading">Loading components…</div>
      ) : projectDetail.components.length === 0 ? (
        <div className="empty-state card">This project has no components yet.</div>
      ) : (
        <div className="component-grid">
          {projectDetail.components.map((c) => (
            <Link key={c.id} to={`/components/${c.id}`} className="component-card">
              {c.has_image && (
                <ComponentImage
                  componentId={c.id}
                  alt={c.name}
                  style={{
                    width: "100%",
                    height: 110,
                    objectFit: "contain",
                    marginBottom: 10,
                    background: "#f4f6f8",
                    borderRadius: 6,
                  }}
                />
              )}
              <h3>{c.name}</h3>
              <div className="muted" style={{ fontSize: 12 }}>
                {c.revision_count} revision{c.revision_count === 1 ? "" : "s"}
              </div>
              {c.latest_revision ? (
                <>
                  <div style={{ margin: "10px 0" }}>
                    <PassFailBadge passesLimit={c.latest_revision.assessment.passes_limit} />
                  </div>
                  <div className="metric-row">
                    <span>Latest ({c.latest_revision.label})</span>
                    <span>
                      {c.latest_revision.assessment.assessed_max_magnitude?.toFixed(1) ?? "–"} mm
                      {c.latest_revision.assessment.assessed_peak_frequency !== null &&
                        ` @ ${c.latest_revision.assessment.assessed_peak_frequency} Hz`}
                    </span>
                  </div>
                </>
              ) : (
                <div className="muted" style={{ fontSize: 12, marginTop: 8 }}>
                  No revisions imported yet
                </div>
              )}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

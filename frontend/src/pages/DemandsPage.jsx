import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { PassFailBadge, StatusBadge } from "../components/Badges";

const STATUSES = ["Open", "In Progress", "Resolved"];

function NewDemandModal({ projects, onClose, onCreated }) {
  const [projectId, setProjectId] = useState(projects[0]?.id ?? "");
  const [components, setComponents] = useState([]);
  const [componentId, setComponentId] = useState("");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!projectId) return;
    api.getProject(projectId).then((detail) => {
      setComponents(detail.components);
      setComponentId(detail.components[0]?.id ?? "");
    });
  }, [projectId]);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!componentId) return;
    setSubmitting(true);
    setError(null);
    try {
      const demand = await api.createDemand({ component_id: Number(componentId), description });
      onCreated(demand);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>New demand</h3>
        <form onSubmit={handleSubmit}>
          <div className="form-row">
            <label>Project</label>
            <select value={projectId} onChange={(e) => setProjectId(e.target.value)}>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>
          <div className="form-row">
            <label>Component</label>
            <select value={componentId} onChange={(e) => setComponentId(e.target.value)}>
              {components.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
          <div className="form-row">
            <label>Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              required
              autoFocus
            />
          </div>
          {error && <div className="banner banner-error">{error}</div>}
          <div className="modal-actions">
            <button type="button" className="btn" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={submitting || !componentId}>
              {submitting ? "Creating…" : "Create demand"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function DemandRow({ demand, onChanged }) {
  const [expanded, setExpanded] = useState(false);
  const [detail, setDetail] = useState(null);
  const [editingDescription, setEditingDescription] = useState(false);
  const [draftDescription, setDraftDescription] = useState(demand.description);
  const [saving, setSaving] = useState(false);

  async function toggleExpand() {
    const next = !expanded;
    setExpanded(next);
    if (next && !detail) {
      const full = await api.getDemand(demand.id);
      setDetail(full);
    }
  }

  async function handleStatusChange(e) {
    const status = e.target.value;
    const updated = await api.updateDemand(demand.id, { status });
    onChanged(updated);
  }

  async function saveDescription() {
    setSaving(true);
    try {
      const updated = await api.updateDemand(demand.id, { description: draftDescription });
      onChanged(updated);
      setEditingDescription(false);
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <tr>
        <td>
          <button className="btn btn-sm" onClick={toggleExpand}>
            {expanded ? "▾" : "▸"}
          </button>
        </td>
        <td>
          <Link to={`/components/${demand.component_id}`}>{demand.component_name}</Link>
          <div className="muted" style={{ fontSize: 11 }}>
            {demand.project_name}
          </div>
        </td>
        <td style={{ maxWidth: 320 }}>
          {editingDescription ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <textarea
                value={draftDescription}
                onChange={(e) => setDraftDescription(e.target.value)}
                style={{ width: "100%" }}
              />
              <div style={{ display: "flex", gap: 6 }}>
                <button className="btn btn-sm btn-primary" onClick={saveDescription} disabled={saving}>
                  Save
                </button>
                <button
                  className="btn btn-sm"
                  onClick={() => {
                    setDraftDescription(demand.description);
                    setEditingDescription(false);
                  }}
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <span onClick={() => setEditingDescription(true)} style={{ cursor: "text" }}>
              {demand.description}
            </span>
          )}
        </td>
        <td>
          <select value={demand.status} onChange={handleStatusChange}>
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </td>
        <td>
          {demand.is_manual ? (
            <span className="muted">Manual</span>
          ) : (
            <span>
              {demand.origin_revision_label}: {demand.origin_value?.toFixed(1)} mm @{" "}
              {demand.origin_frequency} Hz (limit {demand.origin_limit} mm)
            </span>
          )}
        </td>
        <td>
          {demand.latest_revision_label ? (
            <>
              {demand.latest_revision_label} <PassFailBadge passesLimit={demand.latest_passes_limit} />
            </>
          ) : (
            "–"
          )}
        </td>
      </tr>
      {expanded && (
        <tr>
          <td></td>
          <td colSpan={5}>
            <div className="card" style={{ background: "#fafbfc" }}>
              <strong style={{ fontSize: 12 }}>Result across revisions</strong>
              {!detail ? (
                <div className="muted">Loading…</div>
              ) : (
                <table style={{ marginTop: 8 }}>
                  <thead>
                    <tr>
                      <th>Revision</th>
                      <th>Result</th>
                      <th>Peak in range</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {detail.revision_results.map((r) => (
                      <tr key={r.revision_id}>
                        <td>{r.label}</td>
                        <td>
                          <PassFailBadge passesLimit={r.assessment.passes_limit} />
                        </td>
                        <td>
                          {r.assessment.assessed_max_magnitude !== null
                            ? `${r.assessment.assessed_max_magnitude.toFixed(1)} mm @ ${r.assessment.assessed_peak_frequency} Hz`
                            : "–"}
                        </td>
                        <td>{r.is_origin && <span className="badge badge-neutral">Origin finding</span>}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
              <div style={{ marginTop: 10 }}>
                <Link to={`/components/${demand.component_id}`}>View component &amp; compare revisions →</Link>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

export default function DemandsPage() {
  const [demands, setDemands] = useState(null);
  const [projects, setProjects] = useState([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [projectFilter, setProjectFilter] = useState("");
  const [error, setError] = useState(null);
  const [showNewModal, setShowNewModal] = useState(false);

  useEffect(() => {
    api.listProjects().then(setProjects).catch((err) => setError(err.message));
  }, []);

  function load() {
    api
      .listDemands({ status: statusFilter || undefined, projectId: projectFilter || undefined })
      .then(setDemands)
      .catch((err) => setError(err.message));
  }

  useEffect(load, [statusFilter, projectFilter]);

  function handleChanged(updated) {
    setDemands((prev) => prev.map((d) => (d.id === updated.id ? updated : d)));
  }

  const counts = useMemo(() => {
    if (!demands) return {};
    return demands.reduce((acc, d) => {
      acc[d.status] = (acc[d.status] || 0) + 1;
      return acc;
    }, {});
  }, [demands]);

  return (
    <div>
      <div className="page-header">
        <div>
          <h2>Engineering demands</h2>
          <p className="muted" style={{ marginTop: 0 }}>
            Follow-up items raised from failed findings or created manually.
          </p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowNewModal(true)} disabled={!projects.length}>
          New demand
        </button>
      </div>

      {error && <div className="banner banner-error">{error}</div>}

      <div className="toolbar">
        <div className="filters">
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="">All statuses</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {s} {counts[s] ? `(${counts[s]})` : ""}
              </option>
            ))}
          </select>
          <select value={projectFilter} onChange={(e) => setProjectFilter(e.target.value)}>
            <option value="">All projects</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {!demands ? (
        <div className="loading">Loading demands…</div>
      ) : demands.length === 0 ? (
        <div className="empty-state card">No demands match these filters.</div>
      ) : (
        <div className="card" style={{ padding: 0 }}>
          <table>
            <thead>
              <tr>
                <th></th>
                <th>Component / Project</th>
                <th>Description</th>
                <th>Status</th>
                <th>Origin finding</th>
                <th>Latest result</th>
              </tr>
            </thead>
            <tbody>
              {demands.map((d) => (
                <DemandRow key={d.id} demand={d} onChanged={handleChanged} />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showNewModal && (
        <NewDemandModal
          projects={projects}
          onClose={() => setShowNewModal(false)}
          onCreated={(demand) => {
            setShowNewModal(false);
            setDemands((prev) => (prev ? [demand, ...prev] : [demand]));
          }}
        />
      )}
    </div>
  );
}

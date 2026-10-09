import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { PassFailBadge } from "../components/Badges";
import ComponentImage from "../components/ComponentImage";
import CreateDemandModal from "../components/CreateDemandModal";
import FrequencyChart, { SERIES_COLORS } from "../components/FrequencyChart";

export default function ComponentDetailPage() {
  const { componentId } = useParams();
  const [compareData, setCompareData] = useState(null);
  const [selectedIds, setSelectedIds] = useState(null);
  const [error, setError] = useState(null);
  const [demandModalOrigin, setDemandModalOrigin] = useState(null);
  const [createdNotice, setCreatedNotice] = useState(null);

  function load() {
    api
      .compareRevisions(componentId)
      .then((data) => {
        setCompareData(data);
        setSelectedIds(new Set(data.revisions.map((r) => r.revision_id)));
      })
      .catch((err) => setError(err.message));
  }

  useEffect(load, [componentId]);

  const visibleRevisions = useMemo(() => {
    if (!compareData || !selectedIds) return [];
    return compareData.revisions
      .filter((r) => selectedIds.has(r.revision_id))
      .map((r) => ({ ...r, revisionId: r.revision_id }));
  }, [compareData, selectedIds]);

  if (error) return <div className="banner banner-error">{error}</div>;
  if (!compareData) return <div className="loading">Loading component…</div>;

  function toggleRevision(id) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        if (next.size === 1) return next; // keep at least one selected
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }

  return (
    <div>
      <div className="breadcrumbs">
        <Link to={`/?project=${compareData.project_id}`}>{compareData.project_name}</Link> /{" "}
        {compareData.component_name}
      </div>
      <div className="page-header">
        <div style={{ display: "flex", gap: 16, alignItems: "flex-start" }}>
          <ComponentImage
            componentId={componentId}
            alt={compareData.component_name}
            style={{
              width: 88,
              height: 88,
              objectFit: "contain",
              background: "#f4f6f8",
              borderRadius: 8,
              border: "1px solid var(--color-border)",
              flexShrink: 0,
            }}
          />
          <div>
            <h2 style={{ margin: 0 }}>{compareData.component_name}</h2>
            <p className="muted" style={{ marginTop: 4 }}>
              Pass/fail criterion: max magnitude ≤ {compareData.limit_mm} mm for {compareData.freq_min_hz}
              –{compareData.freq_max_hz} Hz inclusive.
            </p>
          </div>
        </div>
      </div>

      {createdNotice && (
        <div className="banner banner-info">
          Demand created for {createdNotice.component_name} ({createdNotice.origin_revision_label || "manual"}).{" "}
          <Link to="/demands">View demands</Link>
        </div>
      )}

      <div className="card">
        <div className="revision-picker">
          {compareData.revisions.map((r, idx) => (
            <label
              key={r.revision_id}
              className={`revision-chip ${selectedIds?.has(r.revision_id) ? "selected" : ""}`}
            >
              <input
                type="checkbox"
                checked={selectedIds?.has(r.revision_id) || false}
                onChange={() => toggleRevision(r.revision_id)}
                style={{ display: "none" }}
              />
              <span className="dot" style={{ background: SERIES_COLORS[idx % SERIES_COLORS.length] }} />
              {r.label}
              <PassFailBadge passesLimit={r.assessment.passes_limit} />
            </label>
          ))}
        </div>

        <FrequencyChart
          revisions={visibleRevisions}
          limitMm={compareData.limit_mm}
          freqMin={compareData.freq_min_hz}
          freqMax={compareData.freq_max_hz}
        />
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Revision comparison</h3>
        <table>
          <thead>
            <tr>
              <th>Revision</th>
              <th>Result ({compareData.freq_min_hz}-{compareData.freq_max_hz} Hz)</th>
              <th>Peak in range</th>
              <th>Δ vs previous</th>
              <th>Overall peak (incl. &gt;{compareData.freq_max_hz} Hz)</th>
              <th>Samples</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {compareData.revisions.map((r) => (
              <tr key={r.revision_id}>
                <td>{r.label}</td>
                <td>
                  <PassFailBadge passesLimit={r.assessment.passes_limit} />
                </td>
                <td>
                  {r.assessment.assessed_max_magnitude !== null
                    ? `${r.assessment.assessed_max_magnitude.toFixed(1)} mm @ ${r.assessment.assessed_peak_frequency} Hz`
                    : "No samples ≤" + compareData.freq_max_hz + " Hz"}
                </td>
                <td>
                  {r.delta_assessed_max_magnitude === null || r.delta_assessed_max_magnitude === undefined
                    ? "–"
                    : `${r.delta_assessed_max_magnitude > 0 ? "+" : ""}${r.delta_assessed_max_magnitude.toFixed(1)} mm`}
                </td>
                <td>
                  {r.assessment.overall_max_magnitude !== null
                    ? `${r.assessment.overall_max_magnitude.toFixed(1)} mm @ ${r.assessment.overall_max_frequency} Hz`
                    : "–"}
                </td>
                <td>{r.samples.length}</td>
                <td>
                  {r.assessment.passes_limit === false && (
                    <button
                      className="btn btn-sm"
                      onClick={() =>
                        setDemandModalOrigin({
                          revisionId: r.revision_id,
                          label: r.label,
                          assessedMaxMagnitude: r.assessment.assessed_max_magnitude,
                          assessedPeakFrequency: r.assessment.assessed_peak_frequency,
                        })
                      }
                    >
                      Create demand
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {demandModalOrigin && (
        <CreateDemandModal
          componentId={Number(componentId)}
          componentName={compareData.component_name}
          origin={demandModalOrigin}
          onClose={() => setDemandModalOrigin(null)}
          onCreated={(demand) => {
            setDemandModalOrigin(null);
            setCreatedNotice(demand);
          }}
        />
      )}
    </div>
  );
}

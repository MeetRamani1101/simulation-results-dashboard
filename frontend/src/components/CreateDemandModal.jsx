import { useState } from "react";
import { api } from "../api/client";

/**
 * origin: optional { revisionId, label, assessedMaxMagnitude, assessedPeakFrequency }
 * describing the failed finding this demand is being raised from. When
 * omitted, the demand is created as a manual (non-finding-linked) entry.
 */
export default function CreateDemandModal({ componentId, componentName, origin, onClose, onCreated }) {
  const [description, setDescription] = useState(
    origin
      ? `${componentName} exceeds the 15 mm limit (${origin.assessedMaxMagnitude?.toFixed(1)} mm at ${origin.assessedPeakFrequency} Hz) in ${origin.label}. Investigate.`
      : ""
  );
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const demand = await api.createDemand({
        component_id: componentId,
        description,
        origin_revision_id: origin ? origin.revisionId : null,
      });
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
        <h3>Create demand</h3>
        <p className="muted" style={{ marginTop: -8, fontSize: 13 }}>
          {componentName}
          {origin ? ` · originating from ${origin.label}` : " · manual entry"}
        </p>
        <form onSubmit={handleSubmit}>
          <div className="form-row">
            <label htmlFor="demand-description">Description</label>
            <textarea
              id="demand-description"
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
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? "Creating…" : "Create demand"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

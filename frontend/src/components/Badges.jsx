export function PassFailBadge({ passesLimit }) {
  if (passesLimit === null || passesLimit === undefined) {
    return <span className="badge badge-neutral">No data ≤50 Hz</span>;
  }
  return passesLimit ? (
    <span className="badge badge-pass">Pass</span>
  ) : (
    <span className="badge badge-fail">Fail</span>
  );
}

const STATUS_CLASS = {
  Open: "badge-open",
  "In Progress": "badge-in-progress",
  Resolved: "badge-resolved",
};

export function StatusBadge({ status }) {
  return <span className={`badge ${STATUS_CLASS[status] || "badge-neutral"}`}>{status}</span>;
}

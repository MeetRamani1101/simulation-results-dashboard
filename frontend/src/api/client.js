const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export function componentImageUrl(componentId) {
  return `${BASE_URL}/api/components/${componentId}/image`;
}

export class ApiError extends Error {
  constructor(message, status, body) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let body = null;
    try {
      body = await res.json();
    } catch {
      /* ignore non-JSON error bodies */
    }
    const message = body?.detail ? JSON.stringify(body.detail) : `Request failed (${res.status})`;
    throw new ApiError(message, res.status, body);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  listProjects: () => request("/api/projects"),
  getProject: (id) => request(`/api/projects/${id}`),
  getComponent: (id) => request(`/api/components/${id}`),
  listRevisions: (componentId) => request(`/api/components/${componentId}/revisions`),
  getRevision: (id) => request(`/api/revisions/${id}`),
  compareRevisions: (componentId, revisionIds) => {
    const qs = revisionIds && revisionIds.length ? `?revision_ids=${revisionIds.join(",")}` : "";
    return request(`/api/components/${componentId}/compare${qs}`);
  },
  listDemands: (filters = {}) => {
    const params = new URLSearchParams();
    if (filters.status) params.set("status", filters.status);
    if (filters.projectId) params.set("project_id", filters.projectId);
    if (filters.componentId) params.set("component_id", filters.componentId);
    const qs = params.toString();
    return request(`/api/demands${qs ? `?${qs}` : ""}`);
  },
  getDemand: (id) => request(`/api/demands/${id}`),
  createDemand: (payload) =>
    request("/api/demands", { method: "POST", body: JSON.stringify(payload) }),
  updateDemand: (id, payload) =>
    request(`/api/demands/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  triggerIngest: () => request("/api/ingest/run", { method: "POST" }),
  latestIngestRun: () => request("/api/ingest/runs/latest"),
};

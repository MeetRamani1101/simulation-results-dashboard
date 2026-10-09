import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { api } from "../api/client";

export default function Layout() {
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState(null);
  const [syncError, setSyncError] = useState(null);

  async function handleSync() {
    setSyncing(true);
    setSyncError(null);
    setSyncResult(null);
    try {
      const run = await api.triggerIngest();
      setSyncResult(run);
    } catch (err) {
      setSyncError(err.message);
    } finally {
      setSyncing(false);
    }
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div>
          <h1>Simulation Results</h1>
          <div className="tagline">Revision review dashboard</div>
        </div>
        <nav>
          <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>
            Projects
          </NavLink>
          <NavLink to="/demands" className={({ isActive }) => (isActive ? "active" : "")}>
            Demands
          </NavLink>
        </nav>
        <div style={{ marginTop: "auto" }}>
          <button className="btn btn-sm" onClick={handleSync} disabled={syncing} style={{ width: "100%" }}>
            {syncing ? "Syncing…" : "Sync data"}
          </button>
          {syncResult && (
            <div style={{ fontSize: 11, color: "#8ea0bd", marginTop: 8, lineHeight: 1.5 }}>
              Scanned {syncResult.files_scanned}: {syncResult.imported_count} new,{" "}
              {syncResult.updated_count} updated, {syncResult.unchanged_count} unchanged.
              {syncResult.error_count > 0 && (
                <div style={{ color: "#ff9a8c", marginTop: 4 }}>
                  {syncResult.error_count} file(s) failed to import.
                </div>
              )}
            </div>
          )}
          {syncError && (
            <div style={{ fontSize: 11, color: "#ff9a8c", marginTop: 8 }}>{syncError}</div>
          )}
        </div>
      </aside>
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}

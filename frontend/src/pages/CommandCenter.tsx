import { useEffect, useState } from "react";
import { api, Dashboard } from "../api";
import { StatCard } from "../components";

export default function CommandCenter() {
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<Dashboard>("/api/dashboard").then(setData).catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="error-banner">{error}</div>;
  if (!data) return <div className="empty">Loading command center...</div>;

  return (
    <>
      <h1>Command Center</h1>
      <p className="page-sub">Live overview of your AI media company - real data only, no simulated metrics.</p>
      <div className="grid cols-4" style={{ marginTop: 16 }}>
        <StatCard label="Active channels" value={data.channels.active} hint={`${data.channels.total} total`} />
        <StatCard label="Active agents" value={data.agents.active} hint={`${data.agents.paused} paused of ${data.agents.total}`} />
        <StatCard label="Tasks queued" value={data.tasks.queued ?? 0}
          hint={`${data.tasks.completed ?? 0} completed · ${data.tasks.failed ?? 0} failed`} />
        <StatCard label="Awaiting approval" value={data.content.awaiting_approval}
          hint={`${data.content.in_production} in production`} />
      </div>

      <div className="grid cols-2" style={{ marginTop: 14 }}>
        <div className="card">
          <div className="card-title">System recommendations</div>
          {data.recommendations.map((rec, i) => (
            <div className="feed-item" key={i}>
              <span>{rec}</span>
            </div>
          ))}
        </div>
        <div className="card">
          <div className="card-title">Activity feed</div>
          {data.recent_events.length === 0 ? (
            <div className="empty">No activity yet - create your first task in Tasks.</div>
          ) : (
            data.recent_events.map((e) => (
              <div className="feed-item" key={e.id}>
                <span className="feed-type">{e.event_type}</span>
                <span style={{ color: "var(--muted)", overflow: "hidden", textOverflow: "ellipsis" }}>
                  {JSON.stringify(e.payload).slice(0, 80)}
                </span>
                <span className="feed-time">{new Date(e.created_at).toLocaleTimeString()}</span>
              </div>
            ))
          )}
        </div>
      </div>

      <div className="grid cols-4" style={{ marginTop: 14 }}>
        <div className="card">
          <div className="card-title">Month-to-date cost</div>
          <div className="stat-value">${data.costs.month_to_date_usd.toFixed(2)}</div>
          <div className="stat-hint">budget ${data.costs.budget_usd}</div>
        </div>
        <div className="card" style={{ gridColumn: "span 3" }}>
          <div className="card-title">Integrations</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {Object.entries(data.integrations).map(([key, status]) => (
              <span key={key} className={`badge ${status === "configured" ? "ok" : "warn"}`}>
                {key}: {status}
              </span>
            ))}
          </div>
          <div className="stat-hint" style={{ marginTop: 8 }}>
            Unconfigured integrations are inert, never simulated. Add keys in backend/.env.
          </div>
        </div>
      </div>
    </>
  );
}

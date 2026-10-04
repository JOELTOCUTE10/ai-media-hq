import { useEffect, useState } from "react";
import { api, Dashboard } from "../api";
import { Icon, StatCard } from "../components";

const EVENT_META: Record<string, { label: string; tone: string }> = {
  TASK_CREATED: { label: "Task created", tone: "accent" },
  TASK_STARTED: { label: "Task started", tone: "accent" },
  TASK_COMPLETED: { label: "Task completed", tone: "ok" },
  TASK_FAILED: { label: "Task failed", tone: "bad" },
  TASK_AUTO_ASSIGNED: { label: "Auto-assigned", tone: "accent" },
  TASK_BLOCKED: { label: "Task blocked", tone: "warn" },
  TASK_CANCELLED: { label: "Task cancelled", tone: "warn" },
  AGENT_STARTED: { label: "Agent working", tone: "accent" },
  AGENT_COMPLETED: { label: "Agent finished", tone: "ok" },
  AGENT_FAILED: { label: "Agent failed", tone: "bad" },
  SUGGESTION_CREATED: { label: "Initiative proposed", tone: "accent" },
  SUGGESTION_APPROVED: { label: "Initiative approved", tone: "ok" },
  SUGGESTION_REJECTED: { label: "Initiative rejected", tone: "warn" },
  RESEARCH_COMPLETED: { label: "Research done", tone: "ok" },
  TREND_DETECTED: { label: "Trend detected", tone: "accent" },
  IDEA_CREATED: { label: "Idea created", tone: "accent" },
  IDEA_APPROVED: { label: "Idea approved", tone: "ok" },
  APPROVAL_REQUESTED: { label: "Approval requested", tone: "warn" },
  APPROVAL_GRANTED: { label: "Approval granted", tone: "ok" },
  APPROVAL_REJECTED: { label: "Approval rejected", tone: "bad" },
  VIDEO_PUBLISHED: { label: "Video published", tone: "ok" },
  PUBLISHING_SCHEDULED: { label: "Publish scheduled", tone: "accent" },
  GOAL_CREATED: { label: "Goal created", tone: "accent" },
  GOAL_COMPLETED: { label: "Goal completed", tone: "ok" },
  OPERATIONS_PAUSED: { label: "Operations paused", tone: "warn" },
  OPERATIONS_RESUMED: { label: "Operations resumed", tone: "ok" },
  BUDGET_EXCEEDED: { label: "Budget exceeded", tone: "bad" },
  ORG_REGISTERED: { label: "Org registered", tone: "ok" },
};

function describe(e: { event_type: string; payload: any }): { label: string; tone: string; detail: string } {
  const meta = EVENT_META[e.event_type] ?? {
    label: e.event_type.toLowerCase().replace(/_/g, " ").replace(/^\\w/, (c) => c.toUpperCase()),
    tone: "muted",
  };
  const p = e.payload ?? {};
  const parts: string[] = [];
  if (typeof p === "string") parts.push(p.length > 70 ? p.slice(0, 70) + "…" : p);
  else if (typeof p === "object") {
    if (p.title) parts.push(`“${p.title}”`);
    if (p.name) parts.push(p.name);
    if (p.attempt) parts.push(`attempt ${p.attempt}`);
    if (p.agent_name) parts.push(p.agent_name);
    if (p.duration_ms) parts.push(`${(p.duration_ms / 1000).toFixed(1)}s${p.cost_usd ? ` · $${p.cost_usd}` : ""}`);
    if (parts.length === 0) {
      const s = JSON.stringify(p);
      if (s && s !== "{}" && s !== '""') parts.push(s.length > 70 ? s.slice(0, 70) + "…" : s);
    }
  }
  return { label: meta.label, tone: meta.tone, detail: parts.join(" · ") };
}

export default function CommandCenter() {
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<Dashboard>("/api/dashboard").then(setData).catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="error-banner">{error}</div>;
  if (!data) return <div className="empty">Loading command center...</div>;

  const configured = Object.entries(data.integrations).filter(([, s]) => s === "configured");
  const inert = Object.entries(data.integrations).length - configured.length;

  return (
    <>
      <h1>Command Center</h1>
      <p className="page-sub">Live overview of your AI media company - real data only, no simulated metrics.</p>
      <div className="grid cols-4" style={{ marginTop: 16 }}>
        <StatCard icon="tv" label="Active channels" value={data.channels.active} hint={`${data.channels.total} total`} />
        <StatCard icon="users" label="Active agents" value={data.agents.active} hint={`${data.agents.paused} paused of ${data.agents.total}`} />
        <StatCard icon="clipboard" label="Tasks queued" value={data.tasks.queued ?? 0}
          hint={`${data.tasks.completed ?? 0} completed · ${data.tasks.failed ?? 0} failed`} />
        <StatCard icon="shield" label="Awaiting approval" value={data.content.awaiting_approval}
          hint={`${data.content.in_production} in production`} />
      </div>

      <div className="grid cols-2" style={{ marginTop: 14 }}>
        <div className="card">
          <div className="card-title">System recommendations</div>
          {data.recommendations.map((rec, i) => (
            <div className="rec-item" key={i}>
              <span className="rec-icon"><Icon name={rec.toLowerCase().includes("no ") || rec.toLowerCase().includes("exceeded") ? "shield" : "sparkle"} /></span>
              <span>{rec}</span>
            </div>
          ))}
        </div>
        <div className="card">
          <div className="card-title">Activity feed</div>
          {data.recent_events.length === 0 ? (
            <div className="empty">No activity yet - create your first task in Tasks.</div>
          ) : (
            data.recent_events.map((e) => {
              const d = describe(e);
              return (
                <div className="feed-item" key={e.id}>
                  <span className={`feed-dot tone-${d.tone}`} />
                  <span className="feed-label">{d.label}</span>
                  <span className="feed-detail">{d.detail}</span>
                  <span className="feed-time">{new Date(e.created_at).toLocaleTimeString()}</span>
                </div>
              );
            })
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
          <div className="int-chips">
            {configured.map(([key]) => (
              <span key={key} className="int-chip ok">{key.replace(/^ai_|^research_|^youtube_/, "")}</span>
            ))}
            {inert > 0 && <span className="int-chip inert">{inert} not configured</span>}
          </div>
          <div className="stat-hint" style={{ marginTop: 10 }}>
            Green chips are live and honest adapters. Anything unconfigured stays inert - never simulated.
          </div>
        </div>
      </div>
    </>
  );
}

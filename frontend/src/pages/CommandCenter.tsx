import { useEffect, useRef, useState } from "react";
import { api, Dashboard, EventItem, GoalSummary, TaskItem } from "../api";
import { Progress, StatCard } from "../components";

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

// Backend emits `type`; be defensive about everything - a feed entry must
// never be able to crash the HQ page again.
function eventType(e: EventItem): string {
  const raw = (e.type ?? e.event_type ?? "") as string;
  return typeof raw === "string" ? raw : "";
}

function describe(e: EventItem): { label: string; tone: string; detail: string; actor: string } {
  const t = eventType(e);
  const meta = EVENT_META[t] ?? {
    label: t ? t.toLowerCase().replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase()) : "System event",
    tone: "muted",
  };
  const p = e.payload ?? {};
  const parts: string[] = [];
  let actor = "";
  if (typeof p === "string") {
    parts.push(p.length > 90 ? p.slice(0, 90) + "…" : p);
  } else if (typeof p === "object" && p !== null) {
    const obj = p as Record<string, unknown>;
    if (typeof obj.title === "string" && obj.title) parts.push(`“${obj.title}”`);
    if (typeof obj.name === "string" && obj.name) parts.push(obj.name);
    if (typeof obj.agent_name === "string" && obj.agent_name) actor = obj.agent_name;
    if (typeof obj.attempt === "number" && obj.attempt) parts.push(`attempt ${obj.attempt}`);
    if (typeof obj.duration_ms === "number" && obj.duration_ms) {
      parts.push(`${(obj.duration_ms / 1000).toFixed(1)}s${typeof obj.cost_usd === "number" && obj.cost_usd ? ` · $${obj.cost_usd}` : ""}`);
    }
    if (parts.length === 0) {
      try {
        const s = JSON.stringify(obj);
        if (s && s !== "{}" && s !== "null") parts.push(s.length > 90 ? s.slice(0, 90) + "…" : s);
      } catch { /* unserializable payload - skip detail */ }
    }
  }
  return { label: meta.label, tone: meta.tone, detail: parts.join(" · "), actor };
}

function toneColor(tone: string): string {
  if (tone === "ok") return "var(--ok)";
  if (tone === "bad") return "var(--bad)";
  if (tone === "warn") return "var(--warn)";
  if (tone === "accent") return "var(--accent)";
  return "var(--muted)";
}

function relTime(iso: string): string {
  const then = new Date(iso).getTime();
  if (!Number.isFinite(then)) return "";
  const s = Math.max(0, Math.floor((Date.now() - then) / 1000));
  if (s < 10) return "just now";
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

function greeting(): string {
  const h = new Date().getHours();
  if (h < 5) return "Late night";
  if (h < 12) return "Good morning";
  if (h < 18) return "Good afternoon";
  return "Good evening";
}

const TASK_LANES: { key: string; label: string }[] = [
  { key: "queued", label: "Queued" },
  { key: "running", label: "Running" },
  { key: "waiting", label: "Waiting" },
  { key: "blocked", label: "Blocked" },
  { key: "completed", label: "Done" },
];

export default function CommandCenter() {
  const [data, setData] = useState<Dashboard | null>(null);
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [goals, setGoals] = useState<GoalSummary[]>([]);
  const [error, setError] = useState("");
  const [newIds, setNewIds] = useState<number[]>([]);
  const [now, setNow] = useState(() => new Date());
  const lastEventId = useRef<number>(0);

  useEffect(() => {
    const tick = setInterval(() => setNow(new Date()), 30000);
    return () => clearInterval(tick);
  }, []);

  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const [dash, taskList, goalList] = await Promise.all([
          api<Dashboard>("/api/dashboard"),
          api<TaskItem[]>("/api/tasks?limit=6").catch(() => [] as TaskItem[]),
          api<GoalSummary[]>("/api/founder/goals").catch(() => [] as GoalSummary[]),
        ]);
        if (!alive) return;
        setData(dash);
        setTasks(Array.isArray(taskList) ? taskList : []);
        setGoals(Array.isArray(goalList) ? goalList.slice(0, 4) : []);
        setError("");
        const events = dash.recent_events ?? [];
        const top = events.length ? Math.max(...events.map((e) => e.id)) : 0;
        if (lastEventId.current > 0) {
          const fresh = events.filter((e) => e.id > lastEventId.current).map((e) => e.id);
          if (fresh.length) {
            setNewIds(fresh);
            setTimeout(() => alive && setNewIds([]), 4000);
          }
        }
        lastEventId.current = Math.max(lastEventId.current, top);
      } catch (e: unknown) {
        if (alive) setError(e instanceof Error ? e.message : "Could not reach the API");
      }
    };
    load();
    const poll = setInterval(load, 15000);
    return () => { alive = false; clearInterval(poll); };
  }, []);

  if (error) return <div className="error-banner">{error}</div>;
  if (!data) return <div className="empty">Booting headquarters...</div>;

  const events = data.recent_events ?? [];
  const configured = Object.entries(data.integrations ?? {}).filter(([, s]) => s === "configured");
  const inert = Object.keys(data.integrations ?? {}).length - configured.length;
  const budgetPct = data.costs.budget_usd > 0 ? Math.min(100, (data.costs.month_to_date_usd / data.costs.budget_usd) * 100) : 0;
  const doneTotal = (data.tasks.completed ?? 0) + (data.tasks.failed ?? 0) + (data.tasks.cancelled ?? 0);

  return (
    <div className="hq">
      <header className="hq-header">
        <div>
          <h1>Company HQ</h1>
          <p className="page-sub">
            {greeting()} - {data.agents.active} of {data.agents.total} agents on duty
            {data.agents.paused ? `, ${data.agents.paused} paused` : ""}. {channelsLine(data.channels.active)}.
          </p>
        </div>
        <div className="hq-header-right">
          <span className="live-pill"><span className="live-dot" /> LIVE</span>
          <span className="hq-clock">
            {now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
            <span className="hq-date"> · {now.toLocaleDateString([], { weekday: "long", month: "short", day: "numeric" })}</span>
          </span>
        </div>
      </header>

      <div className="grid cols-4" style={{ marginTop: 16 }}>
        <StatCard icon="tv" label="Active channels" value={data.channels.active} hint={`${data.channels.total} total`} />
        <StatCard icon="users" label="Agents on duty" value={data.agents.active} hint={`${data.tasks.queued ?? 0} tasks queued`} />
        <StatCard icon="clipboard" label="Tasks completed" value={data.tasks.completed ?? 0} hint={`${doneTotal} processed all-time`} />
        <StatCard icon="shield" label="Awaiting approval" value={data.content.awaiting_approval} hint={`${data.content.in_production} in production`} />
      </div>

      <div className="hq-grid" style={{ marginTop: 14 }}>
        <div className="card hq-feed-card">
          <div className="card-title hq-feed-title">
            <span className="feed-head">Live agent activity</span>
            <span className="hq-feed-count">{events.length ? `${events.length} recent` : "waiting for the first event"}</span>
          </div>
          <div className="hq-feed">
            {events.length === 0 ? (
              <div className="empty">No activity yet - the team posts here the moment anything happens.</div>
            ) : (
              events.map((e) => {
                const d = describe(e);
                const isNew = newIds.includes(e.id);
                const who = d.actor || d.label;
                const initial = (who.replace(/[^a-zA-Z]/g, "")[0] ?? "H").toUpperCase();
                const text = d.detail ? (d.actor ? `${d.label} - ${d.detail}` : d.detail) : d.label;
                return (
                  <div className={`hq-msg${isNew ? " is-new" : ""}`} key={e.id}>
                    <span className="hq-av" style={{ color: toneColor(d.tone), borderColor: toneColor(d.tone) }}>{initial}</span>
                    <div className="hq-bubble">
                      <div className="hq-msg-head">
                        <span className="hq-who">{who}</span>
                        <span className="hq-when">{relTime(e.created_at)}</span>
                      </div>
                      <div className="hq-text">{text}</div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        <div className="hq-rail">
          <div className="card">
            <div className="card-title">Task board</div>
            <div className="hq-board">
              {TASK_LANES.map((lane) => (
                <div className="hq-board-cell" key={lane.key}>
                  <span className="hq-board-num">{data.tasks[lane.key] ?? 0}</span>
                  <span className="hq-board-label">{lane.label}</span>
                </div>
              ))}
            </div>
            {tasks.length > 0 ? (
              <div className="hq-tasklist">
                {tasks.map((t) => (
                  <div className="hq-task" key={t.id}>
                    <span className="hq-task-title">{t.title}</span>
                    <span className={`badge ${t.status === "completed" ? "ok" : t.status === "failed" || t.status === "blocked" ? "bad" : "accent"}`}>
                      {t.status}
                    </span>
                  </div>
                ))}
              </div>
            ) : null}
          </div>

          <div className="card">
            <div className="card-title">Growth</div>
            {goals.length === 0 ? (
              <div className="empty" style={{ padding: "10px 0" }}>No goals set - state one in Founder Mode.</div>
            ) : goals.map((g) => (
              <div className="hq-goal" key={g.id}>
                <div className="hq-goal-head">
                  <span className="hq-goal-title">{g.title}</span>
                  <span className="hq-goal-pct">{g.progress?.pct ?? 0}%</span>
                </div>
                <Progress pct={g.progress?.pct ?? 0} />
                <div className="stat-hint">{g.progress?.completed ?? 0}/{g.progress?.total ?? 0} tasks done</div>
              </div>
            ))}
          </div>

          <div className="card">
            <div className="card-title">Usage & providers</div>
            <div className="hq-meter">
              <div className="hq-meter-bar">
                <div className="hq-meter-fill" style={{ width: `${budgetPct}%` }} />
              </div>
              <div className="hq-meter-row">
                <span>${(data.costs.month_to_date_usd ?? 0).toFixed(2)} this month</span>
                <span className="subtle">of ${data.costs.budget_usd ?? 0} budget</span>
              </div>
            </div>
            <div className="int-chips">
              {configured.map(([key]) => (
                <span key={key} className="int-chip ok">{key.replace(/^ai_|^research_|^youtube_/, "")}</span>
              ))}
              {inert > 0 && <span className="int-chip inert">{inert} unconfigured</span>}
            </div>
            <div className="stat-hint" style={{ marginTop: 10 }}>
              Honest adapters only - unconfigured providers stay inert, never simulated.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function channelsLine(active: number): string {
  if (active === 0) return "no channels are live yet";
  if (active === 1) return "1 channel is live";
  return `${active} channels are live`;
}

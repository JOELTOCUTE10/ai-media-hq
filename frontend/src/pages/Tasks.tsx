import { Fragment, useEffect, useState } from "react";
import { api, Agent, Channel, Task } from "../api";
import { StatusBadge } from "../components";

const COMMAND_EXAMPLES = [
  "Find five strong AI Shorts ideas for this week",
  "Research what's trending in soccer",
  "Create a content plan for tomorrow",
  "Analyze why yesterday's videos performed differently",
];

export default function Tasks() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [error, setError] = useState("");
  const [expanded, setExpanded] = useState<number | null>(null);
  const [form, setForm] = useState({ title: "", agentKey: "chief_strategy", channelSlug: "", priority: "medium" });
  const [busy, setBusy] = useState<number | null>(null);

  async function load() {
    try {
      setTasks(await api<Task[]>("/api/tasks?limit=100"));
    } catch (e: any) { setError(e.message); }
  }
  useEffect(() => {
    load();
    api<Agent[]>("/api/agents").then(setAgents).catch(() => {});
    api<Channel[]>("/api/channels").then(setChannels).catch(() => {});
  }, []);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await api("/api/tasks", {
        method: "POST",
        body: JSON.stringify({
          title: form.title, agent_key: form.agentKey,
          channel_slug: form.channelSlug || undefined, priority: form.priority,
        }),
      });
      setForm({ ...form, title: "" });
      load();
    } catch (err: any) { setError(err.message); }
  }

  async function act(task: Task, action: "run" | "cancel" | "retry") {
    setBusy(task.id);
    setError("");
    try {
      await api(`/api/tasks/${task.id}/${action}`, { method: "POST", body: "{}" });
      load();
    } catch (err: any) { setError(err.message); } finally { setBusy(null); }
  }

  return (
    <>
      <h1>Tasks</h1>
      <p className="page-sub">Give high-level instructions; the orchestrator assigns, checks permissions and executes them.</p>
      <div className="card" style={{ marginTop: 14 }}>
        <div className="card-title">New command</div>
        <form onSubmit={create}>
          <input
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            placeholder={COMMAND_EXAMPLES[Math.floor(Date.now() / 60000) % COMMAND_EXAMPLES.length]}
            required
          />
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr auto", gap: 10, alignItems: "end", marginTop: 8 }}>
            <div><label>Agent</label>
              <select value={form.agentKey} onChange={(e) => setForm({ ...form, agentKey: e.target.value })}>
                {agents.map((a) => <option key={a.key} value={a.key}>{a.name}</option>)}
              </select>
            </div>
            <div><label>Channel</label>
              <select value={form.channelSlug} onChange={(e) => setForm({ ...form, channelSlug: e.target.value })}>
                <option value="">None</option>
                {channels.map((c) => <option key={c.slug} value={c.slug}>{c.name}</option>)}
              </select>
            </div>
            <div><label>Priority</label>
              <select value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value })}>
                {["low", "medium", "high", "urgent"].map((p) => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
            <button className="primary" style={{ marginBottom: 1 }}>Create task</button>
          </div>
        </form>
      </div>
      {error ? <div className="error-banner" style={{ marginTop: 12 }}>{error}</div> : null}
      <div className="card" style={{ marginTop: 14 }}>
        <div className="card-title">Task queue ({tasks.length})</div>
        {tasks.length === 0 ? <div className="empty">No tasks yet.</div> : (
          <table>
            <thead><tr><th>Task</th><th>Agent</th><th>Priority</th><th>Status</th><th>Actions</th></tr></thead>
            <tbody>
              {tasks.map((t) => (
                <Fragment key={t.id}>
                  <tr key={t.id} onClick={() => setExpanded(expanded === t.id ? null : t.id)} style={{ cursor: "pointer" }}>
                    <td>
                      <strong>{t.title}</strong>
                      {t.depends_on.length ? <div style={{ color: "var(--muted)", fontSize: 11 }}>depends on {t.depends_on.join(", ")}</div> : null}
                    </td>
                    <td>{agents.find((a) => a.id === t.assigned_agent_id)?.name ?? "-"}</td>
                    <td><span className="badge">{t.priority}</span></td>
                    <td><StatusBadge status={t.status} /></td>
                    <td>
                      {["queued", "waiting", "failed", "blocked"].includes(t.status) && (
                        <button disabled={busy === t.id} onClick={(e) => { e.stopPropagation(); act(t, "run"); }}>
                          {busy === t.id ? "..." : "Run"}
                        </button>
                      )}
                      {!["completed", "cancelled"].includes(t.status) && (
                        <button className="danger" style={{ marginLeft: 6 }} onClick={(e) => { e.stopPropagation(); act(t, "cancel"); }}>
                          Cancel
                        </button>
                      )}
                    </td>
                  </tr>
                  {expanded === t.id && (
                    <tr>
                      <td colSpan={5}>
                        <div style={{ padding: "4px 0", fontSize: 12.5 }}>
                          <div style={{ color: "var(--muted)", marginBottom: 6 }}>Created {new Date(t.created_at).toLocaleString()} · retries {t.retry_count}</div>
                          {t.error ? <div className="error-banner">{t.error}</div> : null}
                          {t.output?.result ? (
                            <div className="card" style={{ background: "var(--panel-2)" }}>
                              <div className="card-title">Result</div>
                              <div style={{ whiteSpace: "pre-wrap" }}>{String(t.output.result)}</div>
                            </div>
                          ) : null}
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}

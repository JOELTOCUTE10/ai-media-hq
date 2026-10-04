import { useEffect, useState } from "react";
import { api } from "../api";
import { Btn, Empty, Err, Note, Progress } from "../components";

interface Goal { id: number; title: string; description: string; status: string;
  target_date: string | null; progress: { total: number; completed: number; failed: number; pct: number; in_progress: number } }
interface GoalDetail extends Goal { tasks: { id: number; title: string; status: string; assigned_agent_id: number | null }[] }
interface Channel { name: string; slug: string }

const SAMPLE_GOALS = [
  { title: "Grow the AI channel to 10,000 subscribers", description: "Focus on explainers about free AI tools. Publish 3 Shorts per week." },
  { title: "Launch a second channel for soccer highlights", description: "Transformative clips format, publish daily, follow fair-use rules strictly." },
  { title: "Turn this week's trend radar into 5 Shorts", description: "Use the top trends only if they fit our channels; skip anything risky." },
  { title: "Cut production cost per video in half", description: "Audit the pipeline, find the slowest steps, propose concrete fixes." },
];

const Sparkle = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 2l2.2 6.8L21 11l-6.8 2.2L12 20l-2.2-6.8L3 11l6.8-2.2z" />
  </svg>
);

const ArrowUp = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 19V5M5 12l7-7 7 7" />
  </svg>
);

export default function FounderMode() {
  const [goals, setGoals] = useState<Goal[]>([]);
  const [detail, setDetail] = useState<GoalDetail | null>(null);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [provider, setProvider] = useState("");
  const [form, setForm] = useState({ title: "", description: "", channel_slug: "", target_date: "" });

  const load = async () => {
    try {
      setGoals(await api<Goal[]>("/api/founder/goals"));
      setChannels(await api<Channel[]>("/api/channels"));
    } catch (e: any) { setError(e.message); }
  };
  useEffect(() => {
    load();
    api<{ ai_provider?: string }>("/api/health")
      .then((h) => setProvider(h.ai_provider || ""))
      .catch(() => {});
  }, []);

  async function createGoal() {
    if (!form.title.trim()) return;
    try {
      const body: Record<string, any> = { title: form.title, description: form.description };
      if (form.channel_slug) body.channel_slug = form.channel_slug;
      if (form.target_date) body.target_date = form.target_date;
      const r = await api<{ id: number; progress: { total: number } }>("/api/founder/goals", {
        method: "POST", body: JSON.stringify(body) });
      setNote(`Goal created with a real plan: ${r.progress.total} tasks assigned to the agent organization.`);
      setForm({ ...form, title: "", description: "" });
      await load();
    } catch (e: any) { setError(e.message); }
  }

  async function openGoal(id: number) {
    try { setDetail(await api<GoalDetail>(`/api/founder/goals/${id}`)); }
    catch (e: any) { setError(e.message); }
  }

  return (
    <>
      <div className="prompt-hero">
        <h1>State a goal. The company builds it.</h1>
        <div className="page-sub">The system breaks your goal into real tasks with dependencies, agents and tracking.</div>
      </div>
      <Err message={error} /><Note message={note} />
      <div className="prompt-box">
        <input
          className="prompt-input"
          value={form.title}
          onChange={(e) => setForm({ ...form, title: e.target.value })}
          placeholder="Grow the AI channel to 10,000 subscribers..."
          onKeyDown={(e) => { if (e.key === "Enter") createGoal(); }}
        />
        <textarea
          className="prompt-input"
          value={form.description}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
          placeholder="Optional: add context, constraints or a deadline..."
        />
        <div className="prompt-toolbar">
          <span className="auto-pill"><span className="dot" />{provider ? `Auto · ${provider} + failover` : "Auto model"}</span>
          <select value={form.channel_slug} onChange={(e) => setForm({ ...form, channel_slug: e.target.value })}>
            <option value="">all channels</option>
            {channels.map((c) => <option key={c.slug} value={c.slug}>{c.name}</option>)}
          </select>
          <input type="date" value={form.target_date} onChange={(e) => setForm({ ...form, target_date: e.target.value })} />
          <button className="auto-pill surprise" type="button"
            onClick={() => {
              const g = SAMPLE_GOALS[Math.floor(Math.random() * SAMPLE_GOALS.length)];
              setForm({ ...form, title: g.title, description: g.description });
            }}>
            <Sparkle /> Surprise me
          </button>
          <button className="prompt-send" onClick={createGoal} disabled={!form.title.trim()}>
            <ArrowUp /> Create plan
          </button>
        </div>
      </div>
      <div className="card" style={{ marginTop: 16 }}>
        <h3>Goals ({goals.length})</h3>
        {goals.length === 0 ? <Empty>No goals yet. State one above - e.g. "Grow the AI channel".</Empty> : (
          <table>
            <thead><tr><th>Goal</th><th>Progress</th><th>Target</th><th></th></tr></thead>
            <tbody>
              {goals.map((g) => (
                <tr key={g.id}>
                  <td>{g.title}</td>
                  <td><Progress pct={g.progress.pct} /> <span className="subtle">{g.progress.completed}/{g.progress.total} tasks</span></td>
                  <td>{g.target_date ?? "-"}</td>
                  <td><Btn kind="ghost" onClick={() => openGoal(g.id)}>View plan</Btn></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      {detail && (
        <div className="card">
          <div className="page-head"><h3>Plan - {detail.title}</h3>
            <Btn kind="ghost" onClick={() => setDetail(null)}>Close</Btn></div>
          {detail.tasks.length === 0 ? <Empty>No tasks.</Empty> : (
            <table>
              <thead><tr><th>#</th><th>Task</th><th>Status</th></tr></thead>
              <tbody>
                {detail.tasks.map((t) => (
                  <tr key={t.id}><td>{t.id}</td><td>{t.title}</td><td className="mono">{t.status}</td></tr>
                ))}
              </tbody>
            </table>
          )}
          <p className="subtle">Tasks run through the normal agent orchestrator - run them from the Tasks page or let the background runner pick them up.</p>
        </div>
      )}
    </>
  );
}

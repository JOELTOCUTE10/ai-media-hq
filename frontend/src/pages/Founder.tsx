import { useEffect, useState } from "react";
import { api } from "../api";
import { Btn, Empty, Err, Field, Note, Progress } from "../components";

interface Goal { id: number; title: string; description: string; status: string;
  target_date: string | null; progress: { total: number; completed: number; failed: number; pct: number; in_progress: number } }
interface GoalDetail extends Goal { tasks: { id: number; title: string; status: string; assigned_agent_id: number | null }[] }
interface Channel { name: string; slug: string }

export default function FounderMode() {
  const [goals, setGoals] = useState<Goal[]>([]);
  const [detail, setDetail] = useState<GoalDetail | null>(null);
  const [channels, setChannels] = useState<Channel[]>([]);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [form, setForm] = useState({ title: "", description: "", channel_slug: "", target_date: "" });

  const load = async () => {
    try {
      setGoals(await api<Goal[]>("/api/founder/goals"));
      setChannels(await api<Channel[]>("/api/channels"));
    } catch (e: any) { setError(e.message); }
  };
  useEffect(() => { load(); }, []);

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
      <div className="page-head"><h1>Founder Mode</h1>
        <span className="subtle">State a goal; the system breaks it into real tasks with dependencies, agents and tracking.</span></div>
      <Err message={error} /><Note message={note} />
      <div className="card">
        <h3>New goal</h3>
        <div className="form-grid">
          <Field label="Goal"><input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder="Grow the AI channel" /></Field>
          <Field label="Channel (optional)">
            <select value={form.channel_slug} onChange={(e) => setForm({ ...form, channel_slug: e.target.value })}>
              <option value="">all channels</option>
              {channels.map((c) => <option key={c.slug} value={c.slug}>{c.name}</option>)}
            </select>
          </Field>
          <Field label="Target date (optional)">
            <input type="date" value={form.target_date} onChange={(e) => setForm({ ...form, target_date: e.target.value })} />
          </Field>
        </div>
        <Field label="Description"><textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></Field>
        <Btn onClick={createGoal} disabled={!form.title.trim()}>Create goal + plan</Btn>
      </div>
      <div className="card">
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

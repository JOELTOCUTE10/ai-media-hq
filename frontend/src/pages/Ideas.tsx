import { useEffect, useState } from "react";
import { api } from "../api";
import { Btn, Empty, Err, Field, Note, StatusBadge } from "../components";

interface Idea {
  id: number; title: string; topic: string; hook: string; channel: string; channel_slug: string;
  status: string; complexity: string; confidence: number; created_at: string;
}
interface Passport {
  idea: Idea; script_versions: any[]; claims: any[]; quality_checks: any[];
  approvals: any[]; production_jobs: any[]; publishing_jobs: any[];
  analytics: any[]; rights: any[];
}

const STATUS_ORDER = ["candidate", "reviewed", "approved", "production", "published", "analyzed"];

export default function Ideas() {
  const [ideas, setIdeas] = useState<Idea[]>([]);
  const [channels, setChannels] = useState<{ name: string; slug: string }[]>([]);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(0);
  const [passport, setPassport] = useState<Passport | null>(null);
  const [form, setForm] = useState({ channel_slug: "ai-technology", title: "", topic: "", hook: "", description: "" });

  const load = async () => {
    try {
      setIdeas(await api<Idea[]>("/api/ideas"));
      setChannels(await api<{ name: string; slug: string }[]>("/api/channels"));
    } catch (e: any) { setError(e.message); }
  };
  useEffect(() => { load(); }, []);

  async function create() {
    if (!form.title.trim()) return;
    try {
      await api("/api/ideas", { method: "POST", body: JSON.stringify({ ...form, confidence: 0.5 }) });
      setNote("Idea created as candidate.");
      setForm({ ...form, title: "", topic: "", hook: "", description: "" });
      await load();
    } catch (e: any) { setError(e.message); }
  }

  async function advance(id: number, to: string) {
    setBusy(id);
    try {
      await api(`/api/ideas/${id}/status?new_status=${to}`, { method: "POST", body: "{}" });
      await load();
    } catch (e: any) { setError(e.message); } finally { setBusy(0); }
  }

  async function runStrategyRoom(id: number) {
    setBusy(id); setError(""); setNote("");
    try {
      const r = await api<{ completed: number; total: number; synthesis: any }>(`/api/ideas/${id}/strategy-room`, {
        method: "POST", body: "{}" });
      setNote(`Strategy room: ${r.completed}/${r.total} reviews completed.`);
      await load();
    } catch (e: any) { setError(e.message); } finally { setBusy(0); }
  }

  async function openPassport(id: number) {
    try { setPassport(await api<Passport>(`/api/ideas/${id}`)); }
    catch (e: any) { setError(e.message); }
  }

  const nextOf = (s: string) => STATUS_ORDER[Math.min(STATUS_ORDER.indexOf(s) + 1, STATUS_ORDER.length - 1)];

  return (
    <>
      <div className="page-head"><h1>Ideas</h1>
        <span className="subtle">Idea engine - every idea carries its evidence and full Content Passport.</span></div>
      <Err message={error} /><Note message={note} />
      <div className="card">
        <h3>New idea</h3>
        <div className="form-grid">
          <Field label="Channel">
            <select value={form.channel_slug} onChange={(e) => setForm({ ...form, channel_slug: e.target.value })}>
              {channels.map((c) => <option key={c.slug} value={c.slug}>{c.name}</option>)}
            </select>
          </Field>
          <Field label="Title"><input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></Field>
          <Field label="Topic"><input value={form.topic} onChange={(e) => setForm({ ...form, topic: e.target.value })} /></Field>
          <Field label="Hook"><input value={form.hook} onChange={(e) => setForm({ ...form, hook: e.target.value })} /></Field>
        </div>
        <Field label="Description">
          <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        </Field>
        <Btn onClick={create} disabled={!form.title.trim()}>Create idea</Btn>
      </div>
      <div className="card">
        <h3>All ideas ({ideas.length})</h3>
        {ideas.length === 0 ? <Empty>No ideas yet. Create one above or let the agents propose some.</Empty> : (
          <table>
            <thead><tr><th>Title</th><th>Channel</th><th>Status</th><th>Created</th><th></th></tr></thead>
            <tbody>
              {ideas.map((i) => (
                <tr key={i.id}>
                  <td>{i.title}</td>
                  <td>{i.channel}</td>
                  <td><StatusBadge status={i.status} /></td>
                  <td>{new Date(i.created_at).toLocaleDateString()}</td>
                  <td style={{ whiteSpace: "nowrap" }}>
                    <Btn kind="ghost" onClick={() => openPassport(i.id)}>Passport</Btn>{" "}
                    <Btn kind="ghost" onClick={() => runStrategyRoom(i.id)} disabled={busy === i.id}>
                      {busy === i.id ? "Running..." : "Strategy room"}</Btn>{" "}
                    {i.status !== "analyzed" && (
                      <Btn kind="ghost" onClick={() => advance(i.id, nextOf(i.status))} disabled={busy === i.id}>
                        Advance
                      </Btn>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      {passport && (
        <div className="card">
          <div className="page-head">
            <h3>Content Passport - {passport.idea.title}</h3>
            <Btn kind="ghost" onClick={() => setPassport(null)}>Close</Btn>
          </div>
          <p className="subtle">Why was this published? Everything below is the auditable history.</p>
          <div className="kv">
            <span className="k">Status</span><span><StatusBadge status={passport.idea.status} /></span>
            <span className="k">Script versions</span><span>{passport.script_versions.length}</span>
            <span className="k">Claims</span><span>{passport.claims.map((c) => `${c.text.slice(0, 30)}… [${c.status}]`).join(" | ") || "none"}</span>
            <span className="k">QC runs</span><span>{passport.quality_checks.map((q) => `${q.result}`).join(", ") || "none"}</span>
            <span className="k">Approvals</span><span>{passport.approvals.map((a) => a.status).join(", ") || "none"}</span>
            <span className="k">Production</span><span>{passport.production_jobs.map((p) => `${p.provider}:${p.status}`).join(", ") || "none"}</span>
            <span className="k">Publishing</span><span>{passport.publishing_jobs.map((p) => `${p.platform}:${p.status}${p.video_id ? ` (${p.video_id})` : ""}`).join(", ") || "none"}</span>
            <span className="k">Rights</span><span>{passport.rights.map((r) => r.status).join(", ") || "none recorded"}</span>
            <span className="k">Analytics snapshots</span><span>{passport.analytics.length}</span>
          </div>
        </div>
      )}
    </>
  );
}

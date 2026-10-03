import { useEffect, useState } from "react";
import { api } from "../api";
import { Btn, Empty, Err, Field, Note, StatusBadge } from "../components";

interface YtStatus { oauth_app_configured: boolean; channel_connected: boolean; setup_docs: string }
interface Job { id: number; idea_id: number; platform: string; status: string; video_id: string;
  scheduled_at: string | null; published_at: string | null; error: string | null; metadata: Record<string, any> }
interface Idea { id: number; title: string; status: string }

export default function Publishing() {
  const [yt, setYt] = useState<YtStatus | null>(null);
  const [consent, setConsent] = useState("");
  const [jobs, setJobs] = useState<Job[]>([]);
  const [ideas, setIdeas] = useState<Idea[]>([]);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [form, setForm] = useState({ idea_id: 0, title: "", description: "", tags: "", scheduled_at: "" });

  const load = async () => {
    try {
      setYt(await api<YtStatus>("/api/publishing/youtube/status"));
      setJobs(await api<Job[]>("/api/publishing/jobs"));
      const all = await api<Idea[]>("/api/ideas");
      setIdeas(all);
      if (!form.idea_id && all[0]) setForm((f) => ({ ...f, idea_id: all[0].id }));
    } catch (e: any) { setError(e.message); }
  };
  useEffect(() => { load(); }, []);

  async function connect() {
    try {
      const r = await api<{ consent_url: string }>("/api/publishing/youtube/connect");
      setConsent(r.consent_url);
    } catch (e: any) { setError(e.message); }
  }

  async function createJob() {
    try {
      const body: Record<string, any> = {
        idea_id: form.idea_id,
        metadata: { title: form.title, description: form.description,
          tags: form.tags.split(",").map((t) => t.trim()).filter(Boolean) },
      };
      if (form.scheduled_at) body.scheduled_at = new Date(form.scheduled_at).toISOString();
      await api("/api/publishing/jobs", { method: "POST", body: JSON.stringify(body) });
      setNote("Publishing job created. It still passes the readiness gate at publish time.");
      await load();
    } catch (e: any) { setError(e.message); }
  }

  async function publish(id: number) {
    setError(""); setNote("");
    try {
      const r = await api<{ status: string; video_id: string }>(`/api/publishing/jobs/${id}/publish`, {
        method: "POST", body: "{}" });
      setNote(`Published: video id ${r.video_id}`);
    } catch (e: any) {
      setError(e.message);
    }
    await load();
  }

  return (
    <>
      <div className="page-head"><h1>Publishing</h1>
        <span className="subtle">Real YouTube OAuth + resumable uploads. Gate failures and missing credentials are shown exactly as they are.</span></div>
      <Err message={error} /><Note message={note} />
      <div className="card">
        <h3>YouTube connection</h3>
        <div className="kv">
          <span className="k">OAuth app configured</span><span>{yt ? <StatusBadge status={yt.oauth_app_configured ? "configured" : "unconfigured"} /> : "-"}</span>
          <span className="k">Channel connected</span><span>{yt ? <StatusBadge status={yt.channel_connected ? "configured" : "unconfigured"} /> : "-"}</span>
        </div>
        <p className="subtle">Setup: {yt?.setup_docs ?? "-"}</p>
        <Btn onClick={connect} kind="ghost">Get consent URL</Btn>
        {consent && <p className="mono" style={{ wordBreak: "break-all" }}>{consent}</p>}
      </div>
      <div className="card">
        <h3>New publishing job</h3>
        <div className="form-grid">
          <Field label="Idea">
            <select value={form.idea_id} onChange={(e) => setForm({ ...form, idea_id: +e.target.value })}>
              {ideas.map((i) => <option key={i.id} value={i.id}>{i.title}</option>)}
            </select>
          </Field>
          <Field label="Title"><input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></Field>
          <Field label="Description"><input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></Field>
          <Field label="Tags (comma separated)"><input value={form.tags} onChange={(e) => setForm({ ...form, tags: e.target.value })} /></Field>
          <Field label="Schedule (optional)">
            <input type="datetime-local" value={form.scheduled_at} onChange={(e) => setForm({ ...form, scheduled_at: e.target.value })} />
          </Field>
        </div>
        <Btn onClick={createJob} disabled={!form.idea_id}>Create job</Btn>
      </div>
      <div className="card">
        <h3>Jobs ({jobs.length})</h3>
        {jobs.length === 0 ? <Empty>No publishing jobs yet.</Empty> : (
          <table>
            <thead><tr><th>#</th><th>Idea</th><th>Status</th><th>Video id</th><th>When</th><th>Error</th><th></th></tr></thead>
            <tbody>
              {jobs.map((j) => (
                <tr key={j.id}>
                  <td>{j.id}</td>
                  <td>{ideas.find((i) => i.id === j.idea_id)?.title ?? j.idea_id}</td>
                  <td><StatusBadge status={j.status} /></td>
                  <td>{j.video_id || "-"}</td>
                  <td>{j.published_at ? new Date(j.published_at).toLocaleString() : (j.scheduled_at ? `scheduled ${new Date(j.scheduled_at).toLocaleString()}` : "-")}</td>
                  <td style={{ maxWidth: 240 }}>{j.error ?? ""}</td>
                  <td>{j.status !== "published" && <Btn onClick={() => publish(j.id)}>Publish now</Btn>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}

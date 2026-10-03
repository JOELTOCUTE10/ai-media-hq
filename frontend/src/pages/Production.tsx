import { useEffect, useState } from "react";
import { api } from "../api";
import { Btn, Empty, Err, Field, Note, StatusBadge } from "../components";

interface Job { id: number; idea_id: number; provider: string; status: string; cost_usd: number; error: string | null }
interface Asset { id: number; idea_id: number; asset_type: string; url: string }
interface Rights { id: number; idea_id: number; asset_id: number | null; status: string; content_description: string }
interface Idea { id: number; title: string; status: string }

const RIGHTS = ["user_owned", "licensed", "permission_granted", "public_domain", "platform_permitted", "unknown", "blocked"];

export default function Production() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [rights, setRights] = useState<Rights[]>([]);
  const [ideas, setIdeas] = useState<Idea[]>([]);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [jobForm, setJobForm] = useState({ idea_id: 0, provider: "user_media", media_url: "" });
  const [rightsForm, setRightsForm] = useState({ idea_id: 0, asset_id: 0, status: "user_owned", content_description: "", source_url: "" });

  const load = async () => {
    try {
      setJobs(await api<Job[]>("/api/production/jobs"));
      setAssets(await api<Asset[]>("/api/production/assets"));
      setRights(await api<Rights[]>("/api/production/rights"));
      const all = await api<Idea[]>("/api/ideas");
      setIdeas(all);
      if (!jobForm.idea_id && all[0]) setJobForm((f) => ({ ...f, idea_id: all[0].id }));
      if (!rightsForm.idea_id && all[0]) setRightsForm((f) => ({ ...f, idea_id: all[0].id }));
    } catch (e: any) { setError(e.message); }
  };
  useEffect(() => { load(); }, []);

  async function createJob() {
    try {
      await api("/api/production/jobs", {
        method: "POST",
        body: JSON.stringify({ idea_id: jobForm.idea_id, provider: jobForm.provider,
          config: jobForm.provider === "user_media" ? { media_url: jobForm.media_url } : {} }) });
      setNote("Job queued.");
      await load();
    } catch (e: any) { setError(e.message); }
  }

  async function runJob(id: number) {
    setError(""); setNote("");
    try {
      const r = await api<{ status: string }>(`/api/production/jobs/${id}/run`, { method: "POST", body: "{}" });
      setNote(`Job ${id}: ${r.status}.`);
    } catch (e: any) { setError(e.message); }
    await load();
  }

  async function addRights() {
    try {
      await api("/api/production/rights", {
        method: "POST",
        body: JSON.stringify({ ...rightsForm, asset_id: rightsForm.asset_id || null }) });
      setNote("Rights record saved.");
      await load();
    } catch (e: any) { setError(e.message); }
  }

  return (
    <>
      <div className="page-head"><h1>Production</h1>
        <span className="subtle">Provider abstraction: user-supplied media registers as a real asset; external AI providers need credentials and never fake success.</span></div>
      <Err message={error} /><Note message={note} />
      <div className="card">
        <h3>New production job</h3>
        <div className="form-grid">
          <Field label="Idea">
            <select value={jobForm.idea_id} onChange={(e) => setJobForm({ ...jobForm, idea_id: +e.target.value })}>
              {ideas.map((i) => <option key={i.id} value={i.id}>{i.title}</option>)}
            </select>
          </Field>
          <Field label="Provider">
            <select value={jobForm.provider} onChange={(e) => setJobForm({ ...jobForm, provider: e.target.value })}>
              <option value="user_media">user_media (register your own file)</option>
              <option value="external">external (AI video service)</option>
            </select>
          </Field>
          {jobForm.provider === "user_media" && (
            <Field label="Media URL">
              <input value={jobForm.media_url} onChange={(e) => setJobForm({ ...jobForm, media_url: e.target.value })}
                placeholder="https://.../clip.mp4" />
            </Field>
          )}
        </div>
        <Btn onClick={createJob} disabled={!jobForm.idea_id}>Queue job</Btn>
      </div>
      <div className="card">
        <h3>Jobs ({jobs.length})</h3>
        {jobs.length === 0 ? <Empty>No production jobs yet.</Empty> : (
          <table>
            <thead><tr><th>#</th><th>Idea</th><th>Provider</th><th>Status</th><th>Cost</th><th></th></tr></thead>
            <tbody>
              {jobs.map((j) => (
                <tr key={j.id}>
                  <td>{j.id}</td><td>{ideas.find((i) => i.id === j.idea_id)?.title ?? j.idea_id}</td>
                  <td>{j.provider}</td><td><StatusBadge status={j.status} /></td>
                  <td>${j.cost_usd.toFixed(2)}</td>
                  <td>{(j.status === "queued" || j.status === "failed") && <Btn kind="ghost" onClick={() => runJob(j.id)}>Run</Btn>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      <div className="card">
        <h3>Rights management</h3>
        <p className="subtle">Unknown or blocked rights block publishing by default (Section 21).</p>
        <div className="form-grid">
          <Field label="Idea">
            <select value={rightsForm.idea_id} onChange={(e) => setRightsForm({ ...rightsForm, idea_id: +e.target.value })}>
              {ideas.map((i) => <option key={i.id} value={i.id}>{i.title}</option>)}
            </select>
          </Field>
          <Field label="Asset (optional)">
            <select value={rightsForm.asset_id} onChange={(e) => setRightsForm({ ...rightsForm, asset_id: +e.target.value })}>
              <option value={0}>idea-level</option>
              {assets.map((a) => <option key={a.id} value={a.id}>asset #{a.id}</option>)}
            </select>
          </Field>
          <Field label="Rights status">
            <select value={rightsForm.status} onChange={(e) => setRightsForm({ ...rightsForm, status: e.target.value })}>
              {RIGHTS.map((r) => <option key={r}>{r}</option>)}
            </select>
          </Field>
          <Field label="Source URL"><input value={rightsForm.source_url} onChange={(e) => setRightsForm({ ...rightsForm, source_url: e.target.value })} /></Field>
        </div>
        <Btn onClick={addRights} disabled={!rightsForm.idea_id}>Save rights record</Btn>
        {rights.length > 0 && (
          <table style={{ marginTop: 10 }}>
            <thead><tr><th>Idea</th><th>Asset</th><th>Status</th><th>Description</th></tr></thead>
            <tbody>{rights.map((r) => (
              <tr key={r.id}>
                <td>{ideas.find((i) => i.id === r.idea_id)?.title ?? r.idea_id}</td>
                <td>{r.asset_id ?? "idea-level"}</td>
                <td><StatusBadge status={r.status} /></td>
                <td>{r.content_description}</td>
              </tr>
            ))}</tbody>
          </table>
        )}
      </div>
      <div className="card">
        <h3>Assets ({assets.length})</h3>
        {assets.length === 0 ? <Empty>No assets produced yet.</Empty> : (
          <table>
            <thead><tr><th>#</th><th>Idea</th><th>Type</th><th>URL</th></tr></thead>
            <tbody>{assets.map((a) => (
              <tr key={a.id}><td>{a.id}</td><td>{ideas.find((i) => i.id === a.idea_id)?.title ?? a.idea_id}</td>
                <td>{a.asset_type}</td><td><a href={a.url} target="_blank" rel="noreferrer">{a.url}</a></td></tr>
            ))}</tbody>
          </table>
        )}
      </div>
    </>
  );
}

import { useEffect, useState } from "react";
import { api } from "../api";
import { Btn, Empty, Err, Field, Note, StatCard } from "../components";

interface VideoRow { publishing_job_id: number; idea_id: number; title: string; hook: string;
  views: number; retention_pct: number; composite_score: number; likes: number; published_at: string | null }
interface Rollup { channel: string; videos: number; total_views: number; avg_retention_pct: number; subscribers_gained: number }
interface Insight { id: number; observation: string; sample_size: number; recommendation: string; status: string }
interface Job { id: number; idea_id: number; status: string }

export default function Analytics() {
  const [videos, setVideos] = useState<VideoRow[]>([]);
  const [rollup, setRollup] = useState<Rollup[]>([]);
  const [insights, setInsights] = useState<Insight[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [snap, setSnap] = useState({ publishing_job_id: 0, views: 0, retention_pct: 0, watch_time_minutes: 0,
    likes: 0, comments: 0, shares: 0, subscribers_gained: 0 });

  const load = async () => {
    try {
      setVideos(await api<VideoRow[]>("/api/analytics/videos"));
      setRollup(await api<Rollup[]>("/api/analytics/channels"));
      setInsights(await api<Insight[]>("/api/analytics/insights"));
      const j = await api<Job[]>("/api/publishing/jobs");
      setJobs(j);
      if (!snap.publishing_job_id && j[0]) setSnap((s) => ({ ...s, publishing_job_id: j[0].id }));
    } catch (e: any) { setError(e.message); }
  };
  useEffect(() => { load(); }, []);

  async function ingest() {
    try {
      await api("/api/analytics/snapshots", { method: "POST", body: JSON.stringify(snap) });
      setNote("Snapshot ingested. Composite scores updated.");
      await load();
    } catch (e: any) { setError(e.message); }
  }

  async function learn() {
    try {
      const r = await api<any[]>("/api/analytics/learn", { method: "POST", body: "{}" });
      setNote(`Learning engine: ${r.length} insight(s) generated from real data (small samples are reported as insufficient).`);
      await load();
    } catch (e: any) { setError(e.message); }
  }

  return (
    <>
      <div className="page-head"><h1>Analytics</h1>
        <span className="subtle">Composite performance: 40% retention, 30% engagement rate, 30% views vs channel median - not views-only.</span></div>
      <Err message={error} /><Note message={note} />
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 10 }}>
        {rollup.map((r) => (
          <StatCard key={r.channel} label={r.channel} value={r.videos}
            hint={`${r.total_views} views · ${r.avg_retention_pct}% avg retention`} />
        ))}
      </div>
      <div className="card">
        <h3>Ingest metrics snapshot</h3>
        <p className="subtle">Snapshots come from the YouTube API once connected, or manual entry here. Nothing is fabricated.</p>
        <div className="form-grid">
          <Field label="Publishing job">
            <select value={snap.publishing_job_id} onChange={(e) => setSnap({ ...snap, publishing_job_id: +e.target.value })}>
              {jobs.map((j) => <option key={j.id} value={j.id}>job #{j.id} ({j.status})</option>)}
            </select>
          </Field>
          <Field label="Views"><input type="number" value={snap.views} onChange={(e) => setSnap({ ...snap, views: +e.target.value })} /></Field>
          <Field label="Retention %"><input type="number" value={snap.retention_pct} onChange={(e) => setSnap({ ...snap, retention_pct: +e.target.value })} /></Field>
          <Field label="Watch minutes"><input type="number" value={snap.watch_time_minutes} onChange={(e) => setSnap({ ...snap, watch_time_minutes: +e.target.value })} /></Field>
          <Field label="Likes"><input type="number" value={snap.likes} onChange={(e) => setSnap({ ...snap, likes: +e.target.value })} /></Field>
          <Field label="Subscribers gained"><input type="number" value={snap.subscribers_gained} onChange={(e) => setSnap({ ...snap, subscribers_gained: +e.target.value })} /></Field>
        </div>
        <Btn onClick={ingest} disabled={!snap.publishing_job_id}>Ingest snapshot</Btn>{" "}
        <Btn kind="ghost" onClick={learn}>Run learning engine</Btn>
      </div>
      <div className="card">
        <h3>Video performance ({videos.length})</h3>
        {videos.length === 0 ? <Empty>No published videos with metrics yet.</Empty> : (
          <table>
            <thead><tr><th>Title</th><th>Views</th><th>Retention</th><th>Composite</th></tr></thead>
            <tbody>
              {videos.map((v) => (
                <tr key={v.publishing_job_id}>
                  <td>{v.title}</td><td>{v.views.toLocaleString()}</td>
                  <td>{v.retention_pct.toFixed(1)}%</td><td>{v.composite_score.toFixed(1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      <div className="card">
        <h3>Learning insights</h3>
        {insights.length === 0 ? <Empty>No insights yet - run the learning engine after ingesting metrics.</Empty> : (
          insights.map((i) => (
            <div key={i.id} style={{ borderBottom: "1px solid var(--border)", padding: "8px 0" }}>
              <p>{i.observation}</p>
              <p className="subtle">n={i.sample_size} · {i.status} · {i.recommendation}</p>
            </div>
          ))
        )}
      </div>
    </>
  );
}

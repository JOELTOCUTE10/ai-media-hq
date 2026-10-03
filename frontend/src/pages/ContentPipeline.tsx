import { useEffect, useState } from "react";
import { api } from "../api";
import { Btn, Empty, Err, Field, Note, StatusBadge } from "../components";

interface Idea { id: number; title: string; hook: string; status: string; channel: string }

export default function ContentPipeline() {
  const [ideas, setIdeas] = useState<Idea[]>([]);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [sel, setSel] = useState<Idea | null>(null);
  const [script, setScript] = useState<{ hook: string; body: string; cta: string }>({ hook: "", body: "", cta: "" });
  const [claim, setClaim] = useState({ text: "", source_url: "", source_type: "reputable_journalism" });
  const [versions, setVersions] = useState<any[]>([]);
  const [claims, setClaims] = useState<any[]>([]);
  const [qc, setQc] = useState<any>(null);

  const load = async () => {
    try { setIdeas(await api<Idea[]>("/api/ideas")); } catch (e: any) { setError(e.message); }
  };
  useEffect(() => { load(); }, []);

  async function select(idea: Idea) {
    setSel(idea); setQc(null); setError(""); setNote("");
    try {
      const pass = await api<any>(`/api/ideas/${idea.id}`);
      setVersions(pass.script_versions);
      setClaims(pass.claims);
    } catch (e: any) { setError(e.message); }
  }

  async function addScript() {
    if (!sel) return;
    try {
      const s = await api<{ id: number }>(`/api/scripts?idea_id=${sel.id}`, { method: "POST", body: "{}" });
      const v = await api<{ version: number }>(`/api/scripts/${s.id}/versions`, {
        method: "POST", body: JSON.stringify({ ...script, author_agent_key: "script" }) });
      const latest = await api<any>(`/api/scripts/${s.id}/latest`);
      await api(`/api/scripts/${s.id}/versions/${latest.version}/review`, {
        method: "POST", body: JSON.stringify({ decision: "approved" }) });
      setNote(`Script v${v.version} added and approved.`);
      setScript({ hook: "", body: "", cta: "" });
      await select(sel);
    } catch (e: any) { setError(e.message); }
  }

  async function addClaim() {
    if (!sel || !claim.text.trim()) return;
    try {
      await api(`/api/ideas/${sel.id}/claims`, { method: "POST", body: JSON.stringify(claim) });
      setClaim({ ...claim, text: "", source_url: "" });
      await select(sel);
    } catch (e: any) { setError(e.message); }
  }

  async function verify(id: number, status: string) {
    try {
      await api(`/api/ideas/claims/${id}/verify`, {
        method: "POST", body: JSON.stringify({ status, confidence: 0.9, notes: "manual verification" }) });
      if (sel) await select(sel);
    } catch (e: any) { setError(e.message); }
  }

  async function runQc() {
    if (!sel) return;
    try {
      const r = await api<{ result: string; reasons: string[] }>(`/api/qc/run?idea_id=${sel.id}`, {
        method: "POST", body: "{}" });
      setQc(r);
    } catch (e: any) { setError(e.message); }
  }

  return (
    <>
      <div className="page-head"><h1>Content Pipeline</h1>
        <span className="subtle">Script engine, fact checking and quality control for the selected idea.</span></div>
      <Err message={error} /><Note message={note} />
      <div className="card">
        <h3>Select an idea</h3>
        {ideas.length === 0 ? <Empty>Create ideas first (Ideas page).</Empty> : (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {ideas.map((i) => (
              <Btn key={i.id} kind={sel?.id === i.id ? undefined : "ghost"} onClick={() => select(i)}>
                {i.title.slice(0, 34)} · {i.status}
              </Btn>
            ))}
          </div>
        )}
      </div>
      {sel && (
        <>
          <div className="card">
            <h3>Script for "{sel.title}"</h3>
            <div className="form-grid">
              <Field label="Hook"><input value={script.hook} onChange={(e) => setScript({ ...script, hook: e.target.value })} /></Field>
              <Field label="CTA"><input value={script.cta} onChange={(e) => setScript({ ...script, cta: e.target.value })} /></Field>
            </div>
            <Field label="Body"><textarea value={script.body} onChange={(e) => setScript({ ...script, body: e.target.value })} /></Field>
            <Btn onClick={addScript}>Add + approve script version</Btn>
            {versions.length > 0 && (
              <table style={{ marginTop: 10 }}>
                <thead><tr><th>Version</th><th>Hook</th><th>Review</th></tr></thead>
                <tbody>{versions.map((v) => <tr key={v.version}><td>v{v.version}</td><td>{v.hook}</td><td><StatusBadge status={v.review_status} /></td></tr>)}</tbody>
              </table>
            )}
          </div>
          <div className="card">
            <h3>Claims (fact checking)</h3>
            <div className="form-grid">
              <Field label="Claim"><input value={claim.text} onChange={(e) => setClaim({ ...claim, text: e.target.value })} /></Field>
              <Field label="Source URL"><input value={claim.source_url} onChange={(e) => setClaim({ ...claim, source_url: e.target.value })} /></Field>
              <Field label="Source type">
                <select value={claim.source_type} onChange={(e) => setClaim({ ...claim, source_type: e.target.value })}>
                  <option value="primary">primary</option>
                  <option value="official_organization">official_organization</option>
                  <option value="original_research">original_research</option>
                  <option value="reputable_journalism">reputable_journalism</option>
                  <option value="secondary">secondary</option>
                  <option value="social_post">social_post</option>
                </select>
              </Field>
            </div>
            <Btn onClick={addClaim} disabled={!claim.text.trim()}>Add claim</Btn>
            {claims.length > 0 && (
              <table style={{ marginTop: 10 }}>
                <thead><tr><th>Claim</th><th>Status</th><th>Actions</th></tr></thead>
                <tbody>
                  {claims.map((c) => (
                    <tr key={c.id}>
                      <td>{c.text}</td>
                      <td><StatusBadge status={c.status} /></td>
                      <td>
                        <Btn kind="ghost" onClick={() => verify(c.id, "verified")}>Verify</Btn>{" "}
                        <Btn kind="danger" onClick={() => verify(c.id, "disputed")}>Dispute</Btn>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
          <div className="card">
            <h3>Quality control</h3>
            <Btn onClick={runQc}>Run QC</Btn>
            {qc && (
              <div style={{ marginTop: 10 }}>
                <p><StatusBadge status={qc.result} /> {qc.reasons?.join(" ")}</p>
              </div>
            )}
          </div>
        </>
      )}
    </>
  );
}

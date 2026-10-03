import { useEffect, useState } from "react";
import { api } from "../api";
import { Btn, Empty, Err, Field, Note, StatusBadge } from "../components";

interface Exp { id: number; name: string; hypothesis: string; variable: string; control: string;
  variant: string; status: string; conclusion: string | null; confidence: string | null; limitations: string | null }

export default function Experiments() {
  const [exps, setExps] = useState<Exp[]>([]);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [form, setForm] = useState({ name: "", hypothesis: "", variable: "hook", control: "", variant: "" });
  const [resultForm, setResultForm] = useState<{ id: number; n: number; control: number; variant: number }>({ id: 0, n: 0, control: 0, variant: 0 });

  const load = async () => {
    try { setExps(await api<Exp[]>("/api/experiments")); } catch (e: any) { setError(e.message); }
  };
  useEffect(() => { load(); }, []);

  async function create() {
    try {
      await api("/api/experiments", { method: "POST", body: JSON.stringify(form) });
      setNote("Experiment started.");
      setForm({ ...form, name: "", hypothesis: "", control: "", variant: "" });
      await load();
    } catch (e: any) { setError(e.message); }
  }

  async function recordResult() {
    try {
      const r = await api<{ conclusion: string; confidence: string; limitations: string }>(
        `/api/experiments/${resultForm.id}/result`, {
          method: "POST",
          body: JSON.stringify({ sample_size: resultForm.n,
            control_metrics: { retention_pct: resultForm.control },
            variant_metrics: { retention_pct: resultForm.variant } }) });
      setNote(`${r.conclusion} (${r.confidence})`);
      await load();
    } catch (e: any) { setError(e.message); }
  }

  return (
    <>
      <div className="page-head"><h1>Experiments</h1>
        <span className="subtle">Track one variable at a time. Conclusions record sample size and never claim unsupported causation.</span></div>
      <Err message={error} /><Note message={note} />
      <div className="card">
        <h3>New experiment</h3>
        <div className="form-grid">
          <Field label="Name"><input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
          <Field label="Variable"><input value={form.variable} onChange={(e) => setForm({ ...form, variable: e.target.value })} /></Field>
          <Field label="Control"><input value={form.control} onChange={(e) => setForm({ ...form, control: e.target.value })} /></Field>
          <Field label="Variant"><input value={form.variant} onChange={(e) => setForm({ ...form, variant: e.target.value })} /></Field>
        </div>
        <Field label="Hypothesis"><textarea value={form.hypothesis} onChange={(e) => setForm({ ...form, hypothesis: e.target.value })} /></Field>
        <Btn onClick={create} disabled={!form.name.trim()}>Start experiment</Btn>
      </div>
      <div className="card">
        <h3>Record result (retention % comparison)</h3>
        <div className="form-grid">
          <Field label="Experiment">
            <select value={resultForm.id} onChange={(e) => setResultForm({ ...resultForm, id: +e.target.value })}>
              <option value={0}>select...</option>
              {exps.filter((x) => x.status === "running").map((x) => <option key={x.id} value={x.id}>{x.name}</option>)}
            </select>
          </Field>
          <Field label="Sample size"><input type="number" value={resultForm.n} onChange={(e) => setResultForm({ ...resultForm, n: +e.target.value })} /></Field>
          <Field label="Control avg"><input type="number" value={resultForm.control} onChange={(e) => setResultForm({ ...resultForm, control: +e.target.value })} /></Field>
          <Field label="Variant avg"><input type="number" value={resultForm.variant} onChange={(e) => setResultForm({ ...resultForm, variant: +e.target.value })} /></Field>
        </div>
        <Btn onClick={recordResult} disabled={!resultForm.id}>Record result</Btn>
      </div>
      <div className="card">
        <h3>Experiments ({exps.length})</h3>
        {exps.length === 0 ? <Empty>No experiments yet.</Empty> : exps.map((x) => (
          <div key={x.id} style={{ borderBottom: "1px solid var(--border)", padding: "8px 0" }}>
            <p><strong>{x.name}</strong> <StatusBadge status={x.status} /> <span className="subtle">variable: {x.variable} · control "{x.control}" vs variant "{x.variant}"</span></p>
            {x.conclusion && <p className="subtle">{x.conclusion}</p>}
            {x.confidence && <p className="subtle">Confidence: {x.confidence} · {x.limitations}</p>}
          </div>
        ))}
      </div>
    </>
  );
}

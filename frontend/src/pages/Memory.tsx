import { useEffect, useState } from "react";
import { api } from "../api";

interface Mem {
  id: number; scope: string; key: string; content: string;
  channel_id: number | null; agent_id: number | null; tags: string[]; created_at: string;
}

const SCOPES = ["short_term", "long_term", "channel", "agent", "content", "strategic"];

export default function MemoryPage() {
  const [items, setItems] = useState<Mem[]>([]);
  const [q, setQ] = useState("");
  const [scope, setScope] = useState("");
  const [form, setForm] = useState({ scope: "long_term", content: "", key: "" });
  const [error, setError] = useState("");

  async function load() {
    try {
      const params = new URLSearchParams();
      if (q) params.set("q", q);
      if (scope) params.set("scope", scope);
      setItems(await api<Mem[]>(`/api/memory/search?${params}`));
    } catch (e: any) { setError(e.message); }
  }
  useEffect(() => { load(); }, [q, scope]);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    try {
      await api("/api/memory", { method: "POST", body: JSON.stringify(form) });
      setForm({ scope: "long_term", content: "", key: "" });
      load();
    } catch (err: any) { setError(err.message); }
  }

  return (
    <>
      <h1>Memory</h1>
      <p className="page-sub">Searchable shared memory across scopes. Agents retrieve relevant context per task - never full histories.</p>
      <div className="card" style={{ marginTop: 14 }}>
        <div className="card-title">Record memory</div>
        <form onSubmit={save} style={{ display: "grid", gridTemplateColumns: "180px 1fr 180px auto", gap: 10, alignItems: "end" }}>
          <div><label>Scope</label>
            <select value={form.scope} onChange={(e) => setForm({ ...form, scope: e.target.value })}>
              {SCOPES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <div><label>Content</label>
            <input value={form.content} onChange={(e) => setForm({ ...form, content: e.target.value })} required /></div>
          <div><label>Key (optional)</label>
            <input value={form.key} onChange={(e) => setForm({ ...form, key: e.target.value })} /></div>
          <button className="primary">Save</button>
        </form>
      </div>
      {error ? <div className="error-banner" style={{ marginTop: 12 }}>{error}</div> : null}
      <div className="card" style={{ marginTop: 14 }}>
        <div className="card-title">Search</div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 180px", gap: 10 }}>
          <input placeholder="Search memory content or key..." value={q} onChange={(e) => setQ(e.target.value)} />
          <select value={scope} onChange={(e) => setScope(e.target.value)}>
            <option value="">All scopes</option>
            {SCOPES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
        <table style={{ marginTop: 10 }}>
          <thead><tr><th>Scope</th><th>Content</th><th>Created</th></tr></thead>
          <tbody>
            {items.map((m) => (
              <tr key={m.id}>
                <td><span className="badge accent">{m.scope}</span></td>
                <td>{m.content}{m.key ? <span style={{ color: "var(--muted)" }}> · {m.key}</span> : null}</td>
                <td style={{ color: "var(--muted)" }}>{new Date(m.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {items.length === 0 && <div className="empty">No memories found.</div>}
      </div>
    </>
  );
}

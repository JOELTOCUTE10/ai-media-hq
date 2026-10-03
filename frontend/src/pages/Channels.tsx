import { useEffect, useState } from "react";
import { api, Channel } from "../api";

export default function Channels() {
  const [channels, setChannels] = useState<Channel[]>([]);
  const [error, setError] = useState("");
  const [name, setName] = useState("");
  const [niche, setNiche] = useState("");
  const [audience, setAudience] = useState("");

  async function load() {
    try {
      setChannels(await api<Channel[]>("/api/channels"));
    } catch (e: any) {
      setError(e.message);
    }
  }
  useEffect(() => { load(); }, []);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await api("/api/channels", { method: "POST", body: JSON.stringify({ name, niche, audience }) });
      setName(""); setNiche(""); setAudience("");
      load();
    } catch (err: any) {
      setError(err.message);
    }
  }

  return (
    <>
      <h1>Channels</h1>
      <p className="page-sub">Channels are configuration-driven: rules, research sources and style live in data, not code.</p>
      {error ? <div className="error-banner" style={{ marginTop: 12 }}>{error}</div> : null}
      <div className="card" style={{ marginTop: 14 }}>
        <div className="card-title">Add channel</div>
        <form onSubmit={create} style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr auto", gap: 10, alignItems: "end" }}>
          <div><label>Name</label><input value={name} onChange={(e) => setName(e.target.value)} required /></div>
          <div><label>Niche</label><input value={niche} onChange={(e) => setNiche(e.target.value)} /></div>
          <div><label>Audience</label><input value={audience} onChange={(e) => setAudience(e.target.value)} /></div>
          <button className="primary">Add</button>
        </form>
      </div>
      <div className="card" style={{ marginTop: 14 }}>
        <div className="card-title">All channels ({channels.length})</div>
        <table>
          <thead><tr><th>Name</th><th>Niche</th><th>Audience</th><th>Publishing</th><th>Status</th></tr></thead>
          <tbody>
            {channels.map((c) => (
              <tr key={c.id}>
                <td><strong>{c.name}</strong><div style={{ color: "var(--muted)" }}>/{c.slug}</div></td>
                <td>{c.niche}</td>
                <td style={{ maxWidth: 260 }}>{c.audience}</td>
                <td>
                  {String((c.publishing_rules as any)?.cadence_per_week ?? "?")}/week
                  {c.approval_required ? " · approval required" : ""}
                </td>
                <td><span className={`badge ${c.is_active ? "ok" : "warn"}`}>{c.is_active ? "active" : "inactive"}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

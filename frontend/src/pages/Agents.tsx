import { useEffect, useState } from "react";
import { api, Agent } from "../api";
import { StatusBadge } from "../components";

export default function Agents() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [department, setDepartment] = useState("");
  const [error, setError] = useState("");

  async function load() {
    try {
      const q = department ? `?department=${department}` : "";
      setAgents(await api<Agent[]>(`/api/agents${q}`));
    } catch (e: any) {
      setError(e.message);
    }
  }
  useEffect(() => { load(); }, [department]);

  async function toggle(agent: Agent) {
    await api(`/api/agents/${agent.id}/${agent.status === "active" ? "pause" : "resume"}`, { method: "POST" });
    load();
  }

  const departments = ["", "executive", "intelligence", "creative", "production", "quality", "publishing", "growth", "operations"];

  return (
    <>
      <h1>Agents</h1>
      <p className="page-sub">
        {agents.length} AI employees · permissions enforced server-side at every run.
      </p>
      <div style={{ maxWidth: 240, marginTop: 12 }}>
        <label>Filter by department</label>
        <select value={department} onChange={(e) => setDepartment(e.target.value)}>
          {departments.map((d) => <option key={d} value={d}>{d || "All departments"}</option>)}
        </select>
      </div>
      {error ? <div className="error-banner" style={{ marginTop: 12 }}>{error}</div> : null}
      <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(330px, 1fr))", marginTop: 14 }}>
        {agents.map((a) => (
          <div className="card" key={a.id}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start" }}>
              <div>
                <strong>{a.name}</strong>
                <div style={{ color: "var(--muted)", fontSize: 12 }}>{a.role}</div>
              </div>
              <StatusBadge status={a.status} />
            </div>
            <p style={{ color: "var(--muted)", fontSize: 12 }}>{a.description}</p>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 10 }}>
              <span className="badge violet">{a.department}</span>
              <span className="badge accent">{a.permission_level}</span>
              {a.tools.slice(0, 3).map((t) => <span className="badge" key={t}>{t}</span>)}
            </div>
            <button onClick={() => toggle(a)}>{a.status === "active" ? "Pause" : "Resume"}</button>
          </div>
        ))}
      </div>
    </>
  );
}

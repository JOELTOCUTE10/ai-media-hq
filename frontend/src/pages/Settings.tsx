import { useEffect, useState } from "react";
import { api, SettingsBundle } from "../api";

export default function SettingsPage() {
  const [data, setData] = useState<SettingsBundle | null>(null);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const [testing, setTesting] = useState(false);
  const [aiTest, setAiTest] = useState<{ status: string; detail: string } | null>(null);

  async function testAI() {
    setTesting(true); setAiTest(null);
    try {
      setAiTest(await api<{ status: string; detail: string }>("/api/settings/test-ai", { method: "POST" }));
    } catch (e: any) { setAiTest({ status: "error", detail: e.message }); }
    setTesting(false);
  }

  async function load() {
    try { setData(await api<SettingsBundle>("/api/settings")); } catch (e: any) { setError(e.message); }
  }
  useEffect(() => { load(); }, []);

  async function toggle(key: "operations_paused" | "publishing_paused" | "auto_publish" | "agent_initiative" | "auto_approve_suggestions") {
    if (!data) return;
    const next = !data.organization.settings[key];
    try {
      const res = await api<{ organization: { settings: Record<string, any> } }>("/api/settings", {
        method: "PUT", body: JSON.stringify({ [key]: next }),
      });
      setData({ ...data, organization: { ...data.organization, settings: res.organization.settings } });
      setSaved(true); setTimeout(() => setSaved(false), 1500);
    } catch (e: any) { setError(e.message); }
  }

  if (error && !data) return <div className="error-banner">{error}</div>;
  if (!data) return <div className="empty">Loading settings...</div>;

  const switches: [string, string, string][] = [
    ["operations_paused", "Pause all agents (kill switch)", "Blocks every task execution immediately."],
    ["publishing_paused", "Publishing paused", "No content can be published while on."],
    ["auto_publish", "Automatic publishing", "Off = every video needs human approval first."],
    ["agent_initiative", "Agent initiative", "Idle agents propose their own next task (capped 3/day each)."],
    ["auto_approve_suggestions", "Auto-approve suggestions", "Full autonomy: agents queue their own proposals without review."],
  ];

  return (
    <>
      <h1>Settings</h1>
      <p className="page-sub">Global controls for {data.organization.name}. Changes are audit-logged.</p>
      {error ? <div className="error-banner" style={{ marginTop: 12 }}>{error}</div> : null}
      {saved && <div className="badge ok" style={{ marginTop: 10 }}>Saved</div>}
      <div className="grid cols-2" style={{ marginTop: 14 }}>
        <div className="card">
          <div className="card-title">Kill switches & controls</div>
          {switches.map(([key, label, hint]) => (
            <div key={key} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 0", borderBottom: "1px solid var(--border)" }}>
              <div>
                <div>{label}</div>
                <div style={{ color: "var(--muted)", fontSize: 11.5 }}>{hint}</div>
              </div>
              <button
                className={data.organization.settings[key] ? "danger" : ""}
                onClick={() => toggle(key as any)}
              >
                {data.organization.settings[key] ? "ON" : "OFF"}
              </button>
            </div>
          ))}
          <div style={{ marginTop: 10, color: "var(--muted)", fontSize: 12 }}>
            Monthly budget: ${data.system.monthly_budget_usd}
          </div>
        </div>
        <div className="card">
          <div className="card-title">System & integrations</div>
          <div style={{ marginBottom: 10 }}>
            <span className="badge accent">AI provider: {data.system.ai_provider}</span>{" "}
            <span className="badge">{data.system.ai_model}</span>{" "}
            <span className={`badge ${data.system.task_runner_enabled ? "ok" : "warn"}`}>
              runner {data.system.task_runner_enabled ? "enabled" : "disabled"}
            </span>{" "}
            <button className="btn secondary" onClick={testAI} disabled={testing} style={{ marginLeft: 6 }}>
              {testing ? "Testing..." : "Test AI provider"}
            </button>
          </div>
          {aiTest && (
            <div className={aiTest.status === "ok" ? "ok-banner" : "error-banner"} style={{ marginBottom: 10, whiteSpace: "pre-wrap" }}>
              {aiTest.detail}
            </div>
          )}
          <table>
            <thead><tr><th>Integration</th><th>Status</th></tr></thead>
            <tbody>
              {data.integrations.map((i) => (
                <tr key={i.key}>
                  <td>{i.name}</td>
                  <td><span className={`badge ${i.status === "configured" ? "ok" : "warn"}`}>{i.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
          <p style={{ color: "var(--muted)", fontSize: 12, marginTop: 8 }}>
            Add credentials in backend/.env to activate integrations. Nothing is ever simulated.
          </p>
        </div>
      </div>
    </>
  );
}

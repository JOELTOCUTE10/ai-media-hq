import { useEffect, useState } from "react";
import { api } from "../api";
import { Btn, Empty, Err, Note } from "../components";

interface Report { id: number; report_type: string; report_date: string; content: Record<string, any> }

export default function Reports() {
  const [reports, setReports] = useState<Report[]>([]);
  const [sel, setSel] = useState<Report | null>(null);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);

  const load = async () => {
    try {
      const r = await api<Report[]>("/api/reports");
      setReports(r);
      if (!sel && r[0]) setSel(r[0]);
    } catch (e: any) { setError(e.message); }
  };
  useEffect(() => { load(); }, []);

  async function generate() {
    setBusy(true); setError(""); setNote("");
    try {
      const r = await api<{ id: number; content: Record<string, any> }>("/api/reports/daily", {
        method: "POST", body: "{}" });
      setNote("Daily report generated from actual stored data.");
      setSel({ id: r.id, report_type: "daily", report_date: r.content.report_date, content: r.content });
      await load();
    } catch (e: any) { setError(e.message); } finally { setBusy(false); }
  }

  return (
    <>
      <div className="page-head"><h1>Reports</h1>
        <Btn onClick={generate} disabled={busy}>{busy ? "Generating..." : "Generate daily report"}</Btn></div>
      <Err message={error} /><Note message={note} />
      <div style={{ display: "grid", gridTemplateColumns: "240px 1fr", gap: 10 }}>
        <div className="card">
          <h3>History</h3>
          {reports.length === 0 ? <Empty>No reports yet.</Empty> : reports.map((r) => (
            <p key={r.id} style={{ cursor: "pointer", fontWeight: sel?.id === r.id ? 700 : 400 }}
              onClick={() => setSel(r)}>
              {r.report_date} · {r.report_type}
            </p>
          ))}
        </div>
        <div className="card">
          {sel ? (
            <>
              <h3>Daily executive report - {sel.content.report_date}</h3>
              <div className="kv" style={{ marginTop: 10 }}>
                <span className="k">Published today</span>
                <span>{sel.content.videos_published_today?.length ?? 0}</span>
                <span className="k">Awaiting approval</span><span>{sel.content.awaiting_approval ?? 0}</span>
                <span className="k">Work in progress</span><span>{sel.content.work_in_progress ?? 0}</span>
                <span className="k">Costs today / month</span>
                <span>${sel.content.costs?.today_usd ?? 0} / ${sel.content.costs?.month_to_date_usd ?? 0}</span>
                <span className="k">System failures</span>
                <span>{JSON.stringify(sel.content.system_failures ?? {})}</span>
              </div>
              <h4 style={{ marginTop: 12 }}>Top performers</h4>
              {(sel.content.top_performers ?? []).length === 0
                ? <p className="subtle">No analytics data yet (honest reporting).</p>
                : sel.content.top_performers.map((v: any) => <p key={v.idea_id} className="subtle">{v.title} - composite {v.composite_score}</p>)}
              <h4 style={{ marginTop: 12 }}>Trends</h4>
              {(sel.content.trends ?? []).length === 0
                ? <p className="subtle">No trends detected yet.</p>
                : sel.content.trends.map((t: any, i: number) => <p key={i} className="subtle">{t.topic} ({t.lifecycle}, score {t.score?.toFixed?.(0) ?? t.score})</p>)}
              <h4 style={{ marginTop: 12 }}>Recommendations</h4>
              {(sel.content.recommendations ?? []).map((rec: string, i: number) => <p key={i}>- {rec}</p>)}
            </>
          ) : <Empty>Generate your first daily report.</Empty>}
        </div>
      </div>
    </>
  );
}

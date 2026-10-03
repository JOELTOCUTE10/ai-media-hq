import { useEffect, useState } from "react";
import { api } from "../api";
import { Btn, Empty, Err, Note, StatusBadge } from "../components";

interface Trend {
  id: number; topic: string; title: string; lifecycle: string; score: number;
  signals: Record<string, any>; evidence: any[]; last_updated: string;
}

export default function Trends() {
  const [trends, setTrends] = useState<Trend[]>([]);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState<number | null>(null);

  const load = () => api<Trend[]>("/api/trends").then(setTrends).catch((e) => setError(e.message));
  useEffect(() => { load(); }, []);

  async function scan() {
    setBusy(true); setError(""); setNote("");
    try {
      const r = await api<{ trends: Trend[]; message?: string }>("/api/trends/scan", {
        method: "POST", body: JSON.stringify({}) });
      setNote(r.trends?.length
        ? `Scan complete: ${r.trends.length} trend(s) detected from research documents.`
        : (r.message ?? "No research documents yet - run research searches first."));
      await load();
    } catch (e: any) { setError(e.message); } finally { setBusy(false); }
  }

  return (
    <>
      <div className="page-head">
        <h1>Trend Radar</h1>
        <Btn onClick={scan} disabled={busy}>{busy ? "Scanning..." : "Scan now"}</Btn>
      </div>
      <Err message={error} />
      <Note message={note} />
      <div className="card">
        <h3>Detected trends ({trends.length})</h3>
        <p className="subtle">Every score is computed from documented signals - open a trend to see exactly why it was detected.</p>
        {trends.length === 0 ? (
          <Empty>No trends detected yet. Research documents feed the radar; scan after running research.</Empty>
        ) : (
          <table>
            <thead><tr><th>Topic</th><th>Lifecycle</th><th>Score</th><th>Updated</th></tr></thead>
            <tbody>
              {trends.map((t) => (
                <>
                  <tr key={t.id} style={{ cursor: "pointer" }} onClick={() => setOpen(open === t.id ? null : t.id)}>
                    <td>{t.topic}{t.title ? ` - ${t.title}` : ""}</td>
                    <td><StatusBadge status={t.lifecycle} /></td>
                    <td>{t.score.toFixed(0)}</td>
                    <td>{new Date(t.last_updated).toLocaleString()}</td>
                  </tr>
                  {open === t.id && (
                    <tr key={`${t.id}-why`}>
                      <td colSpan={4}>
                        <div className="kv">
                          <span className="k">Why detected (signals)</span>
                          <span className="mono">{JSON.stringify(t.signals, null, 2)}</span>
                          <span className="k">Evidence</span>
                          <span className="mono">{JSON.stringify(t.evidence, null, 2)}</span>
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}

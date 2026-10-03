import { useEffect, useState } from "react";
import { api } from "../api";
import { Empty, Err, StatCard } from "../components";

interface Summary {
  today_usd: number; month_to_date_usd: number; monthly_budget_usd: number; budget_used_pct: number | null;
  by_category: { category: string; amount_usd: number }[];
  by_channel: { channel: string; amount_usd: number }[];
  by_day: { date: string; amount_usd: number }[];
}

export default function Costs() {
  const [s, setS] = useState<Summary | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<Summary>("/api/costs/summary").then(setS).catch((e) => setError(e.message));
  }, []);

  return (
    <>
      <div className="page-head"><h1>Cost Intelligence</h1>
        <span className="subtle">Every dollar is a real recorded operation (agent runs, production, publishing).</span></div>
      <Err message={error} />
      {s && (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 10 }}>
            <StatCard label="Today" value={`$${s.today_usd.toFixed(4)}`} />
            <StatCard label="Month to date" value={`$${s.month_to_date_usd.toFixed(4)}`} />
            <StatCard label="Budget" value={`$${s.monthly_budget_usd.toFixed(2)}`}
              hint={s.budget_used_pct != null ? `${s.budget_used_pct}% used` : "no budget set"} />
          </div>
          {s.budget_used_pct != null && s.budget_used_pct >= 80 && (
            <div className="err-box">Monthly spend is at or above 80% of the configured budget.</div>
          )}
          <div className="card">
            <h3>By category (this month)</h3>
            {s.by_category.length === 0 ? <Empty>No costs recorded this month.</Empty> : (
              <table>
                <thead><tr><th>Category</th><th>Amount</th></tr></thead>
                <tbody>{s.by_category.map((c) => <tr key={c.category}><td>{c.category}</td><td>${c.amount_usd.toFixed(4)}</td></tr>)}</tbody>
              </table>
            )}
          </div>
          <div className="card">
            <h3>By channel (this month)</h3>
            {s.by_channel.length === 0 ? <Empty>No channel costs this month.</Empty> : (
              <table>
                <thead><tr><th>Channel</th><th>Amount</th></tr></thead>
                <tbody>{s.by_channel.map((c) => <tr key={c.channel}><td>{c.channel}</td><td>${c.amount_usd.toFixed(4)}</td></tr>)}</tbody>
              </table>
            )}
          </div>
          <div className="card">
            <h3>By day (this month)</h3>
            {s.by_day.length === 0 ? <Empty>No daily costs yet.</Empty> : (
              <table>
                <thead><tr><th>Date</th><th>Amount</th></tr></thead>
                <tbody>{s.by_day.map((d) => <tr key={d.date}><td>{d.date}</td><td>${d.amount_usd.toFixed(4)}</td></tr>)}</tbody>
              </table>
            )}
          </div>
        </>
      )}
    </>
  );
}

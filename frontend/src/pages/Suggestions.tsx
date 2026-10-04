import { useEffect, useState } from "react";
import { api } from "../api";
import { Empty, Err, Note, Btn, StatusBadge } from "../components";

interface Suggestion {
  id: number;
  agent_id: number;
  agent_name: string;
  agent_department: string;
  title: string;
  description: string;
  rationale: string;
  priority: string;
  status: string;
  task_id: number | null;
  proposed_at: string;
}

const FILTERS = ["proposed", "approved", "rejected", ""] as const;

export default function Suggestions() {
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [proposedCount, setProposedCount] = useState(0);
  const [filter, setFilter] = useState<string>("proposed");
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [busyId, setBusyId] = useState<number | null>(null);
  const [generating, setGenerating] = useState(false);

  async function load(f = filter) {
    setError("");
    try {
      const q = f ? `?status_filter=${f}` : "";
      const body = await api<{ suggestions: Suggestion[]; proposed_count: number }>(`/api/suggestions${q}`);
      setSuggestions(body.suggestions);
      setProposedCount(body.proposed_count);
    } catch (e: any) { setError(e.message); }
  }

  useEffect(() => { load(filter); }, [filter]);

  async function generate() {
    setGenerating(true); setNote("");
    try {
      const res = await api<{ created: number }>("/api/suggestions/generate", { method: "POST" });
      setNote(res.created > 0
        ? `${res.created} new suggestion${res.created > 1 ? "s" : ""} proposed by idle agents.`
        : "No new suggestions right now - agents are busy or hit today's proposal limit.");
      await load();
    } catch (e: any) { setError(e.message); }
    setGenerating(false);
  }

  async function decide(id: number, action: "approve" | "reject") {
    setBusyId(id); setNote(""); setError("");
    try {
      await api(`/api/suggestions/${id}/${action}`, { method: "POST" });
      setNote(action === "approve" ? "Approved - task created and queued for the agent." : "Rejected.");
      await load();
    } catch (e: any) { setError(e.message); }
    setBusyId(null);
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Agent Initiative</h1>
          <p className="page-sub">
            Idle agents propose their own next task with a rationale. Approve to queue it for them.
            Capped at 3 proposals per agent per day; every action is audit-logged.
          </p>
        </div>
        <Btn onClick={generate} disabled={generating}>{generating ? "Asking agents..." : "Generate suggestions"}</Btn>
      </div>
      <Err message={error} />
      <Note message={note} />

      <div className="filter-tabs fade-up">
        {FILTERS.map((f) => (
          <button key={f} className={`filter-tab${filter === f ? " active" : ""}`} onClick={() => setFilter(f)}>
            {f === "" ? "All" : f.charAt(0).toUpperCase() + f.slice(1)}
            {f === "proposed" && proposedCount > 0 ? <span className="tab-count">{proposedCount}</span> : null}
          </button>
        ))}
      </div>

      {suggestions.length === 0 ? (
        <Empty>
          {filter === "proposed"
            ? "No pending suggestions. Idle agents will propose work automatically, or hit \"Generate suggestions\" to ask them now."
            : "Nothing here yet."}
        </Empty>
      ) : (
        <div className="suggestion-grid">
          {suggestions.map((s, i) => (
            <div key={s.id} className="card suggestion-card fade-up" style={{ animationDelay: `${Math.min(i, 12) * 60}ms` }}>
              <div className="suggestion-head">
                <span className="badge accent">{s.agent_name}</span>
                <span className="badge violet">{s.agent_department}</span>
                <span className={`badge priority-${s.priority}`}>{s.priority}</span>
                <span className="suggestion-time">{new Date(s.proposed_at).toLocaleString()}</span>
              </div>
              <div className="suggestion-title">{s.title}</div>
              {s.description ? <div className="suggestion-desc">{s.description}</div> : null}
              {s.rationale ? (
                <div className="suggestion-rationale">
                  <span className="rationale-label">Why</span> {s.rationale}
                </div>
              ) : null}
              <div className="suggestion-actions">
                {s.status === "proposed" ? (
                  <>
                    <Btn onClick={() => decide(s.id, "approve")} disabled={busyId === s.id}>
                      {busyId === s.id ? "..." : "Approve & queue"}
                    </Btn>
                    <Btn kind="ghost" onClick={() => decide(s.id, "reject")} disabled={busyId === s.id}>
                      Reject
                    </Btn>
                  </>
                ) : (
                  <>
                    <StatusBadge status={s.status} />
                    {s.task_id ? <span className="subtle">Task #{s.task_id}</span> : null}
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  );
}

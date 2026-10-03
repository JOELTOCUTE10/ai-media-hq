import { useEffect, useState } from "react";
import { api } from "../api";
import { Btn, Empty, Err, Field, Note, StatusBadge } from "../components";

interface Approval { id: number; idea_id: number; status: string; notes: string; created_at: string }
interface Idea { id: number; title: string; status: string }

export default function Approvals() {
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [ideas, setIdeas] = useState<Idea[]>([]);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [ideaId, setIdeaId] = useState(0);
  const [notes, setNotes] = useState("");

  const load = async () => {
    try {
      setApprovals(await api<Approval[]>("/api/approvals"));
      const all = await api<Idea[]>("/api/ideas");
      setIdeas(all);
      if (!ideaId && all[0]) setIdeaId(all[0].id);
    } catch (e: any) { setError(e.message); }
  };
  useEffect(() => { load(); }, []);

  async function request() {
    try {
      await api("/api/approvals", { method: "POST", body: JSON.stringify({ idea_id: ideaId, notes }) });
      setNote("Approval requested.");
      setNotes("");
      await load();
    } catch (e: any) { setError(e.message); }
  }

  async function decide(id: number, decision: string) {
    try {
      await api(`/api/approvals/${id}/decide`, { method: "POST", body: JSON.stringify({ decision, notes }) });
      setNote(`Approval ${id}: ${decision.replace("_", " ")}.`);
      await load();
    } catch (e: any) { setError(e.message); }
  }

  const pending = approvals.filter((a) => a.status === "pending");
  return (
    <>
      <div className="page-head"><h1>Approvals</h1>
        <span className="subtle">Human approval center - publishing stays gated until you approve (auto-publish can be enabled in Settings).</span></div>
      <Err message={error} /><Note message={note} />
      <div className="card">
        <h3>Request approval</h3>
        <div className="form-grid">
          <Field label="Idea">
            <select value={ideaId} onChange={(e) => setIdeaId(+e.target.value)}>
              {ideas.map((i) => <option key={i.id} value={i.id}>{i.title}</option>)}
            </select>
          </Field>
          <Field label="Notes"><input value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="context for the reviewer" /></Field>
        </div>
        <Btn onClick={request} disabled={!ideaId}>Request approval</Btn>
      </div>
      <div className="card">
        <h3>Pending ({pending.length})</h3>
        {pending.length === 0 ? <Empty>Nothing awaiting approval.</Empty> : (
          <table>
            <thead><tr><th>#</th><th>Idea</th><th>Requested</th><th>Notes</th><th>Actions</th></tr></thead>
            <tbody>
              {pending.map((a) => (
                <tr key={a.id}>
                  <td>{a.id}</td>
                  <td>{ideas.find((i) => i.id === a.idea_id)?.title ?? a.idea_id}</td>
                  <td>{new Date(a.created_at).toLocaleString()}</td>
                  <td>{a.notes}</td>
                  <td style={{ whiteSpace: "nowrap" }}>
                    <Btn onClick={() => decide(a.id, "approved")}>Approve</Btn>{" "}
                    <Btn kind="ghost" onClick={() => decide(a.id, "changes_requested")}>Request changes</Btn>{" "}
                    <Btn kind="danger" onClick={() => decide(a.id, "rejected")}>Reject</Btn>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <h3>History ({approvals.length})</h3>
        {approvals.length > 0 && (
          <table>
            <thead><tr><th>#</th><th>Idea</th><th>Status</th></tr></thead>
            <tbody>{approvals.map((a) => (
              <tr key={a.id}><td>{a.id}</td><td>{ideas.find((i) => i.id === a.idea_id)?.title ?? a.idea_id}</td>
                <td><StatusBadge status={a.status} /></td></tr>
            ))}</tbody>
          </table>
        )}
      </div>
    </>
  );
}

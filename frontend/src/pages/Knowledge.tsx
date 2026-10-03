import { useEffect, useState } from "react";
import { api } from "../api";
import { Btn, Empty, Err, Field, Note } from "../components";

interface Ent { id: number; name: string; entity_type: string; slug: string }
interface Edge { id: number; source: number; target: number; relation: string }

const TYPES = ["topic", "person", "organization", "event", "claim", "source", "video", "trend", "competitor", "concept"];

export default function Knowledge() {
  const [ents, setEnts] = useState<Ent[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [q, setQ] = useState("");
  void setQ;
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [form, setForm] = useState({ entity_type: "topic", name: "" });
  const [rel, setRel] = useState({ source_entity_id: 0, target_entity_id: 0, relation_type: "related_to" });

  const load = async () => {
    try {
      setEnts(await api<Ent[]>(`/api/knowledge/entities?q=${encodeURIComponent(q)}`));
      const g = await api<{ nodes: Ent[]; edges: Edge[] }>("/api/knowledge/graph");
      setEdges(g.edges);
      setError("");
    } catch (e: any) { setError(e.message); }
  };
  useEffect(() => { load(); }, [q]);

  async function addEntity() {
    if (!form.name.trim()) return;
    try {
      await api("/api/knowledge/entities", { method: "POST", body: JSON.stringify(form) });
      setNote(`Entity '${form.name}' saved.`);
      setForm({ ...form, name: "" });
      await load();
    } catch (e: any) { setError(e.message); }
  }

  async function addRel() {
    try {
      await api("/api/knowledge/relationships", { method: "POST", body: JSON.stringify(rel) });
      setNote("Relationship saved.");
      await load();
    } catch (e: any) { setError(e.message); }
  }

  return (
    <>
      <div className="page-head"><h1>Knowledge Base</h1>
        <span className="subtle">Entities, relationships and the knowledge graph (Section 12).</span></div>
      <Err message={error} /><Note message={note} />
      <div className="card">
        <h3>Add entity</h3>
        <div className="form-grid">
          <Field label="Type">
            <select value={form.entity_type} onChange={(e) => setForm({ ...form, entity_type: e.target.value })}>
              {TYPES.map((t) => <option key={t}>{t}</option>)}
            </select>
          </Field>
          <Field label="Name"><input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
        </div>
        <Btn onClick={addEntity} disabled={!form.name.trim()}>Add entity</Btn>
      </div>
      <div className="card">
        <h3>Add relationship</h3>
        <div className="form-grid">
          <Field label="Source entity">
            <select value={rel.source_entity_id} onChange={(e) => setRel({ ...rel, source_entity_id: +e.target.value })}>
              <option value={0}>select...</option>
              {ents.map((e2) => <option key={e2.id} value={e2.id}>{e2.name} ({e2.entity_type})</option>)}
            </select>
          </Field>
          <Field label="Relation"><input value={rel.relation_type} onChange={(e) => setRel({ ...rel, relation_type: e.target.value })} /></Field>
          <Field label="Target entity">
            <select value={rel.target_entity_id} onChange={(e) => setRel({ ...rel, target_entity_id: +e.target.value })}>
              <option value={0}>select...</option>
              {ents.map((e2) => <option key={e2.id} value={e2.id}>{e2.name} ({e2.entity_type})</option>)}
            </select>
          </Field>
        </div>
        <Btn onClick={addRel} disabled={!rel.source_entity_id || !rel.target_entity_id}>Add relationship</Btn>
      </div>
      <div className="card">
        <h3>Entities ({ents.length})</h3>
        {ents.length === 0 ? <Empty>No knowledge entities yet.</Empty> : (
          <table>
            <thead><tr><th>Name</th><th>Type</th></tr></thead>
            <tbody>{ents.map((e) => <tr key={e.id}><td>{e.name}</td><td>{e.entity_type}</td></tr>)}</tbody>
          </table>
        )}
        <h3>Relationships ({edges.length})</h3>
        {edges.length > 0 && (
          <table>
            <thead><tr><th>#</th><th>Source id</th><th>Relation</th><th>Target id</th></tr></thead>
            <tbody>{edges.map((e) => <tr key={e.id}><td>{e.id}</td><td>{e.source}</td><td>{e.relation}</td><td>{e.target}</td></tr>)}</tbody>
          </table>
        )}
      </div>
    </>
  );
}

import { useEffect, useState } from "react";
import { api } from "../api";
import { Btn, Empty, Err, Field, Note } from "../components";

interface Doc {
  id: number; title: string; url: string; topic: string; source_name: string;
  source_type: string; retrieved_at: string; relevance: number;
}

export default function Research() {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [query, setQuery] = useState("");
  const [provider, setProvider] = useState("wikipedia");
  const [topic, setTopic] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");

  const load = () => api<Doc[]>("/api/research/documents").then(setDocs).catch((e) => setError(e.message));
  useEffect(() => { load(); }, []);

  async function search() {
    if (!query.trim()) return;
    setBusy(true); setError(""); setNote("");
    try {
      const r = await api<{ stored: number; provider: string }>("/api/research/search", {
        method: "POST",
        body: JSON.stringify({ query, provider, topic, max_results: 10 }),
      });
      setNote(`Stored ${r.stored} document(s) from ${r.provider}.`);
      await load();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="page-head">
        <h1>Research</h1>
        <span className="subtle">Free providers (Wikipedia, Hacker News, arXiv, OpenAlex) work with no API key. Key-based providers return setup guidance, never fake results.</span>
      </div>
      <Err message={error} />
      <Note message={note} />
      <div className="card">
        <div className="form-grid">
          <Field label="Search query">
            <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="e.g. AI agents news this week" />
          </Field>
          <Field label="Provider">
            <select value={provider} onChange={(e) => setProvider(e.target.value)}>
              <option value="wikipedia">Wikipedia (free, no key)</option>
              <option value="hackernews">Hacker News (free, no key)</option>
              <option value="arxiv">arXiv research (free, no key)</option>
              <option value="openalex">OpenAlex scholarly (free, no key)</option>
              <option value="tavily">Tavily web search (needs key)</option>
              <option value="youtube">YouTube Data API (needs key)</option>
            </select>
          </Field>
          <Field label="Topic tag (optional)">
            <input value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="ai-agents" />
          </Field>
        </div>
        <Btn onClick={search} disabled={busy || !query.trim()}>{busy ? "Searching..." : "Search"}</Btn>
      </div>
      <div className="card">
        <h3>Research documents ({docs.length})</h3>
        {docs.length === 0 ? (
          <Empty>No research documents yet. Run a search once providers are configured (docs/INTEGRATIONS.md).</Empty>
        ) : (
          <table>
            <thead><tr><th>Title</th><th>Topic</th><th>Source</th><th>Type</th><th>Retrieved</th></tr></thead>
            <tbody>
              {docs.map((d) => (
                <tr key={d.id}>
                  <td><a href={d.url} target="_blank" rel="noreferrer">{d.title}</a></td>
                  <td>{d.topic || "-"}</td>
                  <td>{d.source_name || "-"}</td>
                  <td>{d.source_type}</td>
                  <td>{new Date(d.retrieved_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}

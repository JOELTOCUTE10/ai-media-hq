import { useEffect, useState } from "react";
import { HashRouter, Outlet, Route, Routes, useLocation } from "react-router-dom";
import { Sidebar } from "./components";
import { api, clearToken } from "./api";
import Login from "./pages/Login";
import CommandCenter from "./pages/CommandCenter";
import Channels from "./pages/Channels";
import Agents from "./pages/Agents";
import Tasks from "./pages/Tasks";
import SettingsPage from "./pages/Settings";
import MemoryPage from "./pages/Memory";

const PHASES: Record<string, string> = {
  "/research": "Phase 3 - Research intelligence. APIs exist (see docs/ROADMAP.md); UI lands next phase.",
  "/trends": "Phase 3 - The Trend Radar scan API is live (/api/trends); this page ships with the research UI.",
  "/ideas": "Phase 4 - Content Idea Engine. Data models and API are scaffolded; UI next.",
  "/content-pipeline": "Phase 4 - Idea-to-script pipeline with the Strategy Room.",
  "/production": "Phase 5 - Production engine, assets, QC and rights.",
  "/publishing": "Phase 6 - YouTube publishing (OAuth + uploads). Never simulated.",
  "/analytics": "Phase 7 - Analytics ingestion and composite performance.",
  "/experiments": "Phase 7 - Experiment lab with tracked hypotheses.",
  "/knowledge": "Phase 3 - Knowledge graph entities and relationships.",
  "/costs": "Phase 8 - Cost intelligence dashboards (model usage is already tracked per task).",
  "/reports": "Phase 8 - Daily executive report generation.",
};

function Layout() {
  const loc = useLocation();
  const [health, setHealth] = useState<{ status: string; ai_provider: string } | null>(null);
  useEffect(() => {
    api<{ status: string; ai_provider: string }>("/api/health")
      .then(setHealth)
      .catch(() => setHealth(null));
  }, [loc.pathname]);
  return (
    <div className="app">
      <Sidebar />
      <main className="main">
        <div className="topbar">
          <span style={{ color: "var(--muted)", fontSize: 12 }}>
            <span
              className="health-dot"
              style={{ background: health?.status === "ok" ? "var(--ok)" : "var(--bad)" }}
            />
            {health ? `API online · AI provider: ${health.ai_provider}` : "API offline"}
          </span>
          <button onClick={() => { clearToken(); window.location.hash = "#/login"; }}>Sign out</button>
        </div>
        <Outlet />
      </main>
    </div>
  );
}

export default function App() {
  const [authed, setAuthed] = useState(!!localStorage.getItem("token"));
  useEffect(() => {
    const onHash = () => setAuthed(!!localStorage.getItem("token"));
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  return (
    <HashRouter>
      <Routes>
        <Route path="/login" element={<Login onAuthed={() => setAuthed(true)} />} />
        {!authed ? (
          <Route path="*" element={<Login onAuthed={() => setAuthed(true)} />} />
        ) : (
          <>
            <Route element={<Layout />}>
              <Route path="/" element={<CommandCenter />} />
              <Route path="/channels" element={<Channels />} />
              <Route path="/agents" element={<Agents />} />
              <Route path="/tasks" element={<Tasks />} />
              <Route path="/memory" element={<MemoryPage />} />
              <Route path="/settings" element={<SettingsPage />} />
              <Route path="/approvals" element={<Placeholder />} />
              {Object.keys(PHASES).map((path) => (
                <Route key={path} path={path} element={<Placeholder />} />
              ))}
              <Route path="*" element={<Placeholder />} />
            </Route>
          </>
        )}
      </Routes>
    </HashRouter>
  );
}

function Placeholder() {
  const loc = useLocation();
  const note = PHASES[loc.pathname] ?? "This module is on the roadmap (see docs/ROADMAP.md).";
  return (
    <div className="card">
      <h1 style={{ fontSize: 16 }}>{loc.pathname.replace("/", "").replace("-", " ")}</h1>
      <p style={{ color: "var(--muted)" }}>{note}</p>
      <span className="phase-tag">Not yet implemented - never faked</span>
    </div>
  );
}

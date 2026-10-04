import { useEffect, useState } from "react";
import { HashRouter, Outlet, Route, Routes, useLocation } from "react-router-dom";
import { Sidebar } from "./components";
import { api, clearToken } from "./api";
import Login from "./pages/Login";
import CommandCenter from "./pages/CommandCenter";
import Channels from "./pages/Channels";
import Agents from "./pages/Agents";
import Tasks from "./pages/Tasks";
import Suggestions from "./pages/Suggestions";
import SettingsPage from "./pages/Settings";
import MemoryPage from "./pages/Memory";
import Research from "./pages/Research";
import Trends from "./pages/Trends";
import Knowledge from "./pages/Knowledge";
import Ideas from "./pages/Ideas";
import ContentPipeline from "./pages/ContentPipeline";
import Production from "./pages/Production";
import Approvals from "./pages/Approvals";
import Publishing from "./pages/Publishing";
import Analytics from "./pages/Analytics";
import Experiments from "./pages/Experiments";
import Costs from "./pages/Costs";
import Reports from "./pages/Reports";
import FounderMode from "./pages/Founder";

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
              <Route path="/suggestions" element={<Suggestions />} />
              <Route path="/memory" element={<MemoryPage />} />
              <Route path="/settings" element={<SettingsPage />} />
              <Route path="/research" element={<Research />} />
              <Route path="/trends" element={<Trends />} />
              <Route path="/knowledge" element={<Knowledge />} />
              <Route path="/ideas" element={<Ideas />} />
              <Route path="/content-pipeline" element={<ContentPipeline />} />
              <Route path="/production" element={<Production />} />
              <Route path="/approvals" element={<Approvals />} />
              <Route path="/publishing" element={<Publishing />} />
              <Route path="/analytics" element={<Analytics />} />
              <Route path="/experiments" element={<Experiments />} />
              <Route path="/costs" element={<Costs />} />
              <Route path="/reports" element={<Reports />} />
              <Route path="/founder" element={<FounderMode />} />
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
  const note = "This module does not exist yet - it is on the roadmap (see docs/ROADMAP.md).";
  return (
    <div className="card">
      <h1 style={{ fontSize: 16 }}>{loc.pathname.replace("/", "").replace("-", " ")}</h1>
      <p style={{ color: "var(--muted)" }}>{note}</p>
      <span className="phase-tag">Not yet implemented - never faked</span>
    </div>
  );
}

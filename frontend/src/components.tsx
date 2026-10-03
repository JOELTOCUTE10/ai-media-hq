import { NavLink } from "react-router-dom";

export function StatusBadge({ status }: { status: string }) {
  const cls =
    status === "completed" || status === "active" || status === "published" || status === "PASS" || status === "configured"
      ? "ok"
      : status === "failed" || status === "error" || status === "FAIL"
        ? "bad"
        : status === "paused" || status === "blocked" || status === "waiting" || status === "NEEDS_REVIEW"
          ? "warn"
          : status === "queued" || status === "running"
            ? "accent"
            : "";
  return <span className={`badge ${cls}`}>{status}</span>;
}

export function StatCard({ label, value, hint }: { label: string; value: string | number; hint?: string }) {
  return (
    <div className="card">
      <div className="card-title">{label}</div>
      <div className="stat-value">{value}</div>
      {hint ? <div className="stat-hint">{hint}</div> : null}
    </div>
  );
}

export function Empty({ children }: { children: React.ReactNode }) {
  return <div className="empty">{children}</div>;
}

export const NAV: { group: string; items: { to: string; label: string; phase?: string }[] }[] = [
  {
    group: "Command",
    items: [
      { to: "/", label: "Command Center" },
      { to: "/channels", label: "Channels" },
      { to: "/agents", label: "Agents" },
      { to: "/tasks", label: "Tasks" },
    ],
  },
  {
    group: "Intelligence",
    items: [
      { to: "/research", label: "Research", phase: "Phase 3" },
      { to: "/trends", label: "Trends", phase: "Phase 3" },
      { to: "/ideas", label: "Ideas", phase: "Phase 4" },
    ],
  },
  {
    group: "Pipeline",
    items: [
      { to: "/content-pipeline", label: "Content Pipeline", phase: "Phase 4" },
      { to: "/production", label: "Production", phase: "Phase 5" },
      { to: "/approvals", label: "Approvals" },
      { to: "/publishing", label: "Publishing", phase: "Phase 6" },
    ],
  },
  {
    group: "Growth & Ops",
    items: [
      { to: "/analytics", label: "Analytics", phase: "Phase 7" },
      { to: "/experiments", label: "Experiments", phase: "Phase 7" },
      { to: "/knowledge", label: "Knowledge", phase: "Phase 3" },
      { to: "/memory", label: "Memory" },
      { to: "/costs", label: "Costs", phase: "Phase 8" },
      { to: "/reports", label: "Reports", phase: "Phase 8" },
    ],
  },
  {
    group: "System",
    items: [{ to: "/settings", label: "Settings" }],
  },
];

export function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="logo">
        AI MEDIA <span className="hq">HQ</span>
      </div>
      <div className="logo-sub">AI media company operating system</div>
      {NAV.map((group) => (
        <div className="nav-group" key={group.group}>
          <div className="nav-group-label">{group.group}</div>
          {group.items.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => `nav-item${isActive ? " active" : ""}`}
            >
              {item.label}
            </NavLink>
          ))}
        </div>
      ))}
    </aside>
  );
}

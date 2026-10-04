import { NavLink } from "react-router-dom";
import { LogoLockup } from "./components/Logo";

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

export const NAV: { group: string; items: { to: string; label: string }[] }[] = [
  {
    group: "Command",
    items: [
      { to: "/", label: "Command Center" },
      { to: "/founder", label: "Founder Mode" },
      { to: "/channels", label: "Channels" },
      { to: "/agents", label: "Agents" },
      { to: "/tasks", label: "Tasks" },
      { to: "/suggestions", label: "Initiative" },
    ],
  },
  {
    group: "Intelligence",
    items: [
      { to: "/research", label: "Research" },
      { to: "/trends", label: "Trends" },
      { to: "/knowledge", label: "Knowledge" },
    ],
  },
  {
    group: "Pipeline",
    items: [
      { to: "/ideas", label: "Ideas" },
      { to: "/content-pipeline", label: "Content Pipeline" },
      { to: "/production", label: "Production" },
      { to: "/approvals", label: "Approvals" },
      { to: "/publishing", label: "Publishing" },
    ],
  },
  {
    group: "Growth & Ops",
    items: [
      { to: "/analytics", label: "Analytics" },
      { to: "/experiments", label: "Experiments" },
      { to: "/memory", label: "Memory" },
      { to: "/costs", label: "Costs" },
      { to: "/reports", label: "Reports" },
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
      <div style={{ padding: "2px 4px 14px" }}>
        <LogoLockup size={36} />
      </div>
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

export function Btn({ children, onClick, kind, disabled }: {
  children: React.ReactNode; onClick?: () => void; kind?: "ghost" | "danger"; disabled?: boolean;
}) {
  return (
    <button className={`btn ${kind ?? ""}`} onClick={onClick} disabled={disabled}>
      {children}
    </button>
  );
}

export function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="field">
      <label>{label}</label>
      {children}
    </div>
  );
}

export function Err({ message }: { message: string }) {
  if (!message) return null;
  return <div className="err-box">{message}</div>;
}

export function Note({ message }: { message: string }) {
  if (!message) return null;
  return <div className="ok-box">{message}</div>;
}

export function Progress({ pct }: { pct: number }) {
  return (
    <div className="progress-outer" title={`${pct}%`}>
      <div className="progress-inner" style={{ width: `${Math.min(100, Math.max(0, pct))}%` }} />
    </div>
  );
}


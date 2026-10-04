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

export function StatCard({ label, value, hint, icon }: { label: string; value: string | number; hint?: string; icon?: string }) {
  return (
    <div className="card stat-card">
      <div className="card-title stat-title">
        {icon ? <span className="stat-icon"><Icon name={icon} /></span> : null}
        {label}
      </div>
      <div className="stat-value">{value}</div>
      {hint ? <div className="stat-hint">{hint}</div> : null}
    </div>
  );
}

export function Empty({ children }: { children: React.ReactNode }) {
  return <div className="empty">{children}</div>;
}


// --- stroke icon set (16px, currentColor) ---
const ICONS: Record<string, string> = {
  grid: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="10" y="10" width="7" height="7" rx="1.5"/><path d="M10 6.5h4.5a1.5 1.5 0 0 1 1.5 1.5v4.5"/>',
  compass: '<circle cx="12" cy="12" r="9"/><path d="M15.5 8.5l-2 5-5 2 2-5z"/>',
  tv: '<rect x="3" y="6" width="14" height="10" rx="2"/><path d="M8 3l4 3 4-3"/>',
  users: '<circle cx="9" cy="8" r="3"/><path d="M3.5 16c.6-2.8 2.8-4.2 5.5-4.2S13.9 13.2 14.5 16"/><circle cx="15.5" cy="9" r="2.3"/><path d="M15 11.9c2.2.2 3.6 1.5 4.1 3.6"/>',
  clipboard: '<rect x="5" y="4" width="10" height="13" rx="2"/><path d="M9 4.5V3h2v1.5"/><path d="M8.5 9h4M8.5 12.5h4"/>',
  bulb: '<path d="M9 18h4M10 21h2"/><path d="M12 3a6 6 0 0 0-3.6 10.8c.6.5 1 1.2 1.1 2.2h5c.1-1 .5-1.7 1.1-2.2A6 6 0 0 0 12 3z"/>',
  search: '<circle cx="10.5" cy="10.5" r="6"/><path d="M15 15l4.5 4.5"/>',
  trend: '<path d="M3 17l5-5 3.5 3.5L18 9"/><path d="M14.5 9H18v3.5"/>',
  book: '<path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H19v14H6.5A2.5 2.5 0 0 0 4 19.5z"/><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H19v4H6.5A2.5 2.5 0 0 1 4 19.5z" fill="none"/>',
  sparkle: '<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z"/><path d="M18.5 15.5l.8 2.2 2.2.8-2.2.8-.8 2.2-.8-2.2-2.2-.8 2.2-.8z"/>',
  layers: '<path d="M12 3l8 4.5-8 4.5-8-4.5z"/><path d="M4 12l8 4.5 8-4.5"/><path d="M4 16.5L12 21l8-4.5"/>',
  film: '<rect x="3" y="4" width="14" height="12" rx="2"/><path d="M7 4v12M13 4v12M3 8h14M3 12h14"/>',
  shield: '<path d="M12 3l7 3v5c0 4.4-3 8-7 10-4-2-7-5.6-7-10V6z"/><path d="M9 11.5l2 2 4-4"/>',
  cloud: '<path d="M7 18a4 4 0 0 1-.5-8 5.5 5.5 0 0 1 10.7 1.2A3.5 3.5 0 0 1 17 18z"/><path d="M12 12v6M9.5 15.5L12 13l2.5 2.5"/>',
  chart: '<path d="M4 20V10M9.5 20V4M15 20v-8M20.5 20V7"/>',
  flask: '<path d="M10 3v5.5L5.5 16A3 3 0 0 0 8.2 20.5h7.6A3 3 0 0 0 18.5 16L14 8.5V3"/><path d="M8.5 3h7M7.5 13h9"/>',
  db: '<ellipse cx="12" cy="5.5" rx="7" ry="2.5"/><path d="M5 5.5v13c0 1.4 3.1 2.5 7 2.5s7-1.1 7-2.5v-13"/><path d="M5 12c0 1.4 3.1 2.5 7 2.5s7-1.1 7-2.5"/>',
  dollar: '<path d="M12 3v18"/><path d="M16 6.5c0-1.7-1.8-2.5-4-2.5s-4 1-4 2.8 1.6 2.4 4 3.2 4.5 1.4 4.5 3.5-2 3-4.5 3-4.3-1.1-4.5-2.8"/>',
  file: '<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4M9 12h5M9 16h5"/>',
  gear: '<circle cx="12" cy="12" r="3"/><path d="M12 2.5v2.2M12 19.3v2.2M2.5 12h2.2M19.3 12h2.2M5.3 5.3l1.6 1.6M17.1 17.1l1.6 1.6M18.7 5.3l-1.6 1.6M6.9 17.1l-1.6 1.6"/>',
};

export function Icon({ name, size = 16 }: { name: string; size?: number }) {
  const path = ICONS[name] ?? ICONS.grid;
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
      <g dangerouslySetInnerHTML={{ __html: path }} />
    </svg>
  );
}

export const NAV_ICONS: Record<string, string> = {
  "/": "grid", "/founder": "compass", "/channels": "tv", "/agents": "users",
  "/tasks": "clipboard", "/suggestions": "bulb", "/research": "search",
  "/trends": "trend", "/knowledge": "book", "/ideas": "sparkle",
  "/content-pipeline": "layers", "/production": "film", "/approvals": "shield",
  "/publishing": "cloud", "/analytics": "chart", "/experiments": "flask",
  "/memory": "db", "/costs": "dollar", "/reports": "file", "/settings": "gear",
};

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
              <Icon name={NAV_ICONS[item.to] ?? "grid"} />
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


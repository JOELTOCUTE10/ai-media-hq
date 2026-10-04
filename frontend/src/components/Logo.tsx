export function LogoMark({ size = 34, glow = true }: { size?: number; glow?: boolean }) {
  return (
    <svg
      width={size} height={size} viewBox="0 0 48 48" fill="none"
      style={glow ? { filter: "drop-shadow(0 0 10px rgba(34,211,238,.45))" } : undefined}
    >
      <defs>
        <linearGradient id="lg1" x1="0" y1="0" x2="48" y2="48">
          <stop offset="0%" stopColor="#22d3ee" />
          <stop offset="55%" stopColor="#818cf8" />
          <stop offset="100%" stopColor="#c084fc" />
        </linearGradient>
        <linearGradient id="lg2" x1="0" y1="48" x2="48" y2="0">
          <stop offset="0%" stopColor="#22d3ee" />
          <stop offset="100%" stopColor="#a78bfa" />
        </linearGradient>
      </defs>
      {/* rounded-diamond badge */}
      <path
        d="M24 2 L44 14 L44 34 L24 46 L4 34 L4 14 Z"
        rx="4"
        stroke="url(#lg1)" strokeWidth="2.4" fill="rgba(12,18,34,.85)"
      />
      {/* signal waves */}
      <path d="M14 17 a 12 12 0 0 1 0 14" stroke="url(#lg2)" strokeWidth="2.2" strokeLinecap="round" fill="none" opacity=".85" />
      <path d="M10 13 a 17 17 0 0 1 0 22" stroke="url(#lg2)" strokeWidth="2.2" strokeLinecap="round" fill="none" opacity=".4" />
      {/* play triangle */}
      <path d="M21 19.5 L29.5 24 L21 28.5 Z" fill="url(#lg1)" />
    </svg>
  );
}

export function LogoLockup({ size = 34, sub = true }: { size?: number; sub?: boolean }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
      <LogoMark size={size} />
      <div>
        <div className="logo" style={{ margin: 0 }}>AI MEDIA <span className="hq">HQ</span></div>
        {sub ? <div className="logo-sub" style={{ marginBottom: 0 }}>Autonomous media company OS</div> : null}
      </div>
    </div>
  );
}

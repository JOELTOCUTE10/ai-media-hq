import { useEffect, useState } from "react";
import { LogoMark } from "./Logo";

/**
 * Full-screen opening animation: the logo draws in, the name fades up with
 * a shimmer bar, then the whole splash dissolves into the app.
 * Shown once per browser session (skip on hot re-navigation).
 */
export default function Splash({ onDone }: { onDone: () => void }) {
  const [leaving, setLeaving] = useState(false);

  useEffect(() => {
    const t1 = setTimeout(() => setLeaving(true), 2100);
    const t2 = setTimeout(onDone, 2700);
    return () => { clearTimeout(t1); clearTimeout(t2); };
  }, [onDone]);

  return (
    <div className={`splash${leaving ? " splash-leave" : ""}`}>
      <div className="splash-inner">
        <div className="splash-logo">
          <LogoMark size={92} />
        </div>
        <div className="splash-name">
          AI MEDIA <span className="hq">HQ</span>
        </div>
        <div className="splash-sub">Autonomous media company · OS</div>
        <div className="splash-bar"><div className="splash-bar-fill" /></div>
        <div className="splash-status">Booting agents…</div>
      </div>
      <div className="aurora a1" /><div className="aurora a2" /><div className="aurora a3" />
    </div>
  );
}

import React from "react";

/**
 * Production safety net: if any component throws during render, show a clear
 * recovery card instead of a silently blank page. The error is also stored on
 * window.__uiError and mirrored into document.title so remote QA (and curious
 * engineers with a devtools console) can see what happened.
 */
export default class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { error: Error | null }
> {
  state: { error: Error | null } = { error: null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  componentDidCatch(error: Error) {
    try {
      (window as unknown as Record<string, unknown>).__uiError = {
        message: error.message,
        stack: String(error.stack ?? ""),
        at: new Date().toISOString(),
      };
      document.title = "AI Media HQ (UI error)";
    } catch {
      /* never let the reporter itself crash */
    }
  }

  render() {
    if (this.state.error) {
      return (
        <div className="card" style={{ margin: 24, borderColor: "var(--bad)", maxWidth: 640 }}>
          <div className="card-title" style={{ color: "var(--bad)" }}>Interface error</div>
          <div style={{ fontSize: 15, fontWeight: 600 }}>Something in this page hit an unexpected error.</div>
          <p className="subtle" style={{ marginTop: 6 }}>
            Your data is safe on the server - this is a display problem only. Reload to get back to work.
          </p>
          <pre className="error-pre">{String(this.state.error.stack ?? this.state.error)}</pre>
          <button className="btn" onClick={() => window.location.reload()}>Reload</button>
        </div>
      );
    }
    return this.props.children;
  }
}

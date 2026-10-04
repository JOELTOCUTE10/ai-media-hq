import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./theme.css";

// Global error telemetry: any uncaught browser error is recorded where a
// devtools console (or remote QA session) can read it, and the tab title
// flips so a broken page is never silently blank.
window.addEventListener("error", (e) => {
  try {
    (window as unknown as Record<string, unknown>).__uiError = {
      message: e.message,
      stack: String((e.error as Error | undefined)?.stack ?? ""),
      at: new Date().toISOString(),
    };
    document.title = "AI Media HQ (UI error)";
  } catch {
    /* reporting must never throw */
  }
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

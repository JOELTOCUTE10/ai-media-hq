import { useState } from "react";
import { api, clearToken, setToken } from "../api";
import { LogoMark } from "../components/Logo";

export default function Login({ onAuthed }: { onAuthed: () => void }) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [orgName, setOrgName] = useState("My Media Company");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const path = mode === "login" ? "/api/auth/login" : "/api/auth/register";
      const body = mode === "login"
        ? { email, password }
        : { email, password, organization_name: orgName };
      const res = await api<{ access_token: string }>(path, {
        method: "POST",
        body: JSON.stringify(body),
      });
      setToken(res.access_token);
      await api("/api/auth/me");
      onAuthed();
      window.location.hash = "#/";
    } catch (err: any) {
      clearToken();
      setError(err?.message || "Sign in failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-wrap">
      <div className="aurora a1" /><div className="aurora a2" /><div className="aurora a3" />
      <div className="login-col">
        <div className="login-hero">
          <h2>Run your media company<span className="accent-i">.</span></h2>
          <p>An autonomous team of AI agents researches, scripts, produces and publishes - you approve.</p>
        </div>
        <form className="card login-card" onSubmit={submit}>
        <div className="login-brand">
          <LogoMark size={56} />
          <div className="login-title">AI MEDIA <span className="hq">HQ</span></div>
          <div className="login-tag">{mode === "login" ? "Operating center" : "Create your company"}</div>
        </div>
        {error ? <div className="error-banner">{error}</div> : null}
        {mode === "register" ? (
          <div className="login-f1">
            <label>Organization name</label>
            <input value={orgName} onChange={(e) => setOrgName(e.target.value)} required />
          </div>
        ) : null}
        <div className="login-f2">
          <label>Email</label>
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </div>
        <div className="login-f3">
          <label>Password {mode === "register" ? "(min 8 characters)" : ""}</label>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </div>
        <button className="primary" style={{ width: "100%", marginTop: 18 }} disabled={busy}>
          {busy ? "Working..." : mode === "login" ? "Sign in" : "Create account"}
        </button>
        <p style={{ color: "var(--muted)", fontSize: 12, textAlign: "center", marginTop: 14, marginBottom: 0 }}>
          {mode === "login" ? "No account yet? " : "Already registered? "}
          <a href="#" onClick={(e) => { e.preventDefault(); setMode(mode === "login" ? "register" : "login"); }}>
            {mode === "login" ? "Create one" : "Sign in"}
          </a>
        </p>
      </form>
      </div>
    </div>
  );
}

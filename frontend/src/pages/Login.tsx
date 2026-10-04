import { useState } from "react";
import { api, clearToken, setToken } from "../api";

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
      <form className="card login-card" onSubmit={submit}>
        <div className="logo" style={{ fontSize: 20 }}>AI MEDIA <span className="hq">HQ</span></div>
        <div className="page-sub" style={{ marginBottom: 14 }}>
          {mode === "login" ? "Sign in to your operating center" : "Create your media company account"}
        </div>
        {error ? <div className="error-banner">{error}</div> : null}
        {mode === "register" ? (
          <>
            <label>Organization name</label>
            <input value={orgName} onChange={(e) => setOrgName(e.target.value)} required />
          </>
        ) : null}
        <label>Email</label>
        <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <label>Password {mode === "register" ? "(min 8 characters)" : ""}</label>
        <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        <button className="primary" style={{ width: "100%", marginTop: 16 }} disabled={busy}>
          {busy ? "Working..." : mode === "login" ? "Sign in" : "Create account"}
        </button>
        <p style={{ color: "var(--muted)", fontSize: 12, textAlign: "center", marginTop: 12 }}>
          {mode === "login" ? "No account yet? " : "Already registered? "}
          <a href="#" onClick={(e) => { e.preventDefault(); setMode(mode === "login" ? "register" : "login"); }}>
            {mode === "login" ? "Create one" : "Sign in"}
          </a>
        </p>
      </form>
    </div>
  );
}

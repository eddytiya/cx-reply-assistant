import { useRef, useState } from "react";
import { api } from "../api";

export default function LoginPage({ onLoggedIn, onRegister, initialUsername = "", notice = "" }) {
  const [role, setRole] = useState("customer");
  const [username, setUsername] = useState(initialUsername);
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const lock = useRef(false);

  async function login(event) {
    event.preventDefault();
    if (lock.current || !username.trim() || !password) return;
    lock.current = true;
    setBusy(true);
    setError("");
    try {
      const user = await api("/auth/login", {
        method: "POST",
        body: { username: username.trim(), password, role },
      });
      setPassword("");
      onLoggedIn(user);
    } catch (error) {
      setError(error.message);
    } finally {
      lock.current = false;
      setBusy(false);
    }
  }

  function selectRole(next) {
    setRole(next);
    setPassword("");
    setError("");
    setShowPassword(false);
  }

  return (
    <main className="login-page">
      <section className="login-card" aria-labelledby="login-title">
        <div className="login-icon" aria-hidden="true">CX</div>
        <p className="eyebrow">CX REPLY ASSISTANT</p>
        <h1 id="login-title">Welcome back</h1>
        <p className="login-description">Log in to your customer or administrator account.</p>
        <div className="tabs" role="group" aria-label="Account type">
          <button type="button" disabled={busy} aria-pressed={role === "customer"} onClick={() => selectRole("customer")}>Customer</button>
          <button type="button" disabled={busy} aria-pressed={role === "admin"} onClick={() => selectRole("admin")}>Administrator</button>
        </div>
        {notice && <p className="login-notice" role="status">{notice}</p>}
        <form onSubmit={login}>
          <fieldset disabled={busy}>
            <label htmlFor="login-username">Username</label>
            <input id="login-username" name="username" autoComplete="username" autoCapitalize="none" spellCheck={false} maxLength={60} required value={username} onChange={(event) => setUsername(event.target.value)} />
            <label htmlFor="login-password">Password</label>
            <div className="password-field">
              <input id="login-password" name="password" type={showPassword ? "text" : "password"} autoComplete="current-password" maxLength={128} required value={password} onChange={(event) => setPassword(event.target.value)} />
              <button type="button" className="password-toggle" aria-label={showPassword ? "Hide password" : "Show password"} aria-pressed={showPassword} onClick={() => setShowPassword((value) => !value)}>{showPassword ? "Hide" : "Show"}</button>
            </div>
            {error && <p className="error" role="alert">{error}</p>}
            <button className="primary login-submit" disabled={busy || !username.trim() || !password}>{busy ? "Logging in..." : `Log in as ${role === "admin" ? "administrator" : "customer"}`}</button>
          </fieldset>
        </form>
        {role === "customer" && <p className="login-footer">New customer? <button type="button" className="text-button" disabled={busy} onClick={onRegister}>Create an account</button></p>}
      </section>
    </main>
  );
}

import { useEffect, useState } from "react";
import { api } from "../api";
import App from "../App";
import LoginPage from "./LoginPage";
import RegisterPage from "./RegisterPage";

export default function AuthRoot() {
  const [user, setUser] = useState(null);
  const [checking, setChecking] = useState(true);
  const [error, setError] = useState("");
  const [version, setVersion] = useState(0);
  const [screen, setScreen] = useState("login");
  const [username, setUsername] = useState("");
  const [notice, setNotice] = useState("");
  const [loggingOut, setLoggingOut] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    async function restore() {
      try {
        const account = await api("/auth/me", { signal: controller.signal });
        if (!controller.signal.aborted) setUser(account);
      } catch (error) {
        if (!controller.signal.aborted) {
          setUser(null);
          if (error.status !== 401) setError(error.message);
        }
      } finally {
        if (!controller.signal.aborted) setChecking(false);
      }
    }
    restore();
    return () => controller.abort();
  }, [version]);

  useEffect(() => {
    function expire() {
      setUser(null);
      setScreen("login");
      setNotice("Your session expired. Please log in again.");
    }
    window.addEventListener("auth:expired", expire);
    return () => window.removeEventListener("auth:expired", expire);
  }, []);

  async function logout() {
    if (loggingOut) return;
    setLoggingOut(true);
    setError("");
    try {
      await api("/auth/logout", { method: "POST" });
      setUser(null);
      setScreen("login");
      setUsername("");
      setNotice("You have been logged out.");
    } catch (error) {
      setError(error.message);
    } finally {
      setLoggingOut(false);
    }
  }

  if (checking) return <main className="login-page"><p role="status">Checking your session...</p></main>;
  if (error && !user) return <main className="login-page"><section className="login-card"><p className="error" role="alert">{error}</p><button onClick={() => { setChecking(true); setError(""); setVersion((value) => value + 1); }}>Retry connection</button></section></main>;
  if (user) return <><div className="session-bar"><span>Signed in as <strong>{user.display_name}</strong> · {user.role}</span><button onClick={logout} disabled={loggingOut}>{loggingOut ? "Logging out..." : "Log out"}</button>{error && <p className="error" role="alert">{error}</p>}</div><App key={`${user.role}:${user.id}`} user={user} /></>;
  if (screen === "register") return <RegisterPage onLogin={() => { setScreen("login"); setNotice(""); }} onRegistered={(name, message) => { setUsername(name); setNotice(message); setScreen("login"); }} />;
  return <LoginPage key={username} initialUsername={username} notice={notice} onRegister={() => { setNotice(""); setScreen("register"); }} onLoggedIn={(account) => { setUser(account); setNotice(""); }} />;
}

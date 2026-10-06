import { useRef, useState } from "react";
import { api, useLoad } from "../api";
import { usernameError } from "../username";

export default function RegisterPage({ onRegistered, onLogin }) {
  const brands = useLoad("/auth/brands");
  const [form, setForm] = useState({ name: "", email: "", username: "", password: "", confirmPassword: "", brand_id: "" });
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const lock = useRef(false);

  function change(event) {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }));
    setError("");
  }

  async function register(event) {
    event.preventDefault();
    if (lock.current) return;
    setError("");
    if (!form.name.trim()) { setError("Enter your name."); return; }
    const validationError = usernameError(form.username);
    if (validationError) { setError(validationError); return; }
    if (form.password !== form.confirmPassword) { setError("Passwords do not match."); return; }
    lock.current = true;
    setBusy(true);
    try {
      const result = await api("/auth/register", {
        method: "POST",
        body: { name: form.name.trim(), email: form.email.trim(), username: form.username.trim(), password: form.password, brand_id: form.brand_id },
      });
      onRegistered(form.username.trim().toLowerCase(), result.message);
    } catch (error) {
      setError(error.message);
    } finally {
      lock.current = false;
      setBusy(false);
    }
  }

  return (
    <main className="login-page">
      <section className="login-card" aria-labelledby="register-title">
        <div className="login-icon" aria-hidden="true">CX</div>
        <p className="eyebrow">CUSTOMER ACCOUNT</p>
        <h1 id="register-title">Create your account</h1>
        <p className="login-description">Choose the brand you want to contact. Your account gets its own support conversation.</p>
        {brands.loading && <p role="status">Loading brands...</p>}
        {brands.error && <div role="alert"><p className="error">{brands.error}</p><button onClick={brands.refresh}>Retry</button></div>}
        <form onSubmit={register}>
          <fieldset disabled={busy || brands.loading || Boolean(brands.error)}>
            <label>Full name<input name="name" value={form.name} onChange={change} autoComplete="name" maxLength={120} required /></label>
            <label>Email<input name="email" type="email" value={form.email} onChange={change} autoComplete="email" required /></label>
            <label>Username<input name="username" value={form.username} onChange={change} autoComplete="username" autoCapitalize="none" spellCheck={false} maxLength={60} required aria-describedby="username-help" /></label>
            <small id="username-help">Use letters, numbers, dots, underscores, or hyphens.</small>
            <label>Brand<select name="brand_id" value={form.brand_id} onChange={change} required><option value="">Select a brand</option>{(brands.data || []).map((brand) => <option key={brand.id} value={brand.id}>{brand.name}</option>)}</select></label>
            <label>Password<input name="password" type={showPassword ? "text" : "password"} value={form.password} onChange={change} autoComplete="new-password" minLength={8} maxLength={128} required /></label>
            <label>Confirm password<input name="confirmPassword" type={showPassword ? "text" : "password"} value={form.confirmPassword} onChange={change} autoComplete="new-password" minLength={8} maxLength={128} required /></label>
            <label className="checkbox-label"><input type="checkbox" checked={showPassword} onChange={(event) => setShowPassword(event.target.checked)} />Show passwords</label>
            <small>Use at least 8 characters. Passwords are stored as hashes.</small>
            {error && <p className="error" role="alert">{error}</p>}
            <button className="primary login-submit" disabled={busy || !form.brand_id}>{busy ? "Creating account..." : "Register as customer"}</button>
          </fieldset>
        </form>
        <p className="login-footer">Already registered? <button type="button" className="text-button" disabled={busy} onClick={onLogin}>Log in</button></p>
      </section>
    </main>
  );
}

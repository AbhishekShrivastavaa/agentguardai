import { useState } from "react";
import { Shield } from "lucide-react";
import { useAuth } from "../context/AuthContext.jsx";

export default function Login() {
  const { login, register } = useAuth();
  const [isRegister, setIsRegister] = useState(false);
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      if (isRegister) {
        await register(username.trim(), email.trim(), password);
      }
      await login(username.trim(), password);
    } catch (err) {
      setError(err.message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  return <main className="auth-page"><section className="auth-card">
    <div className="auth-logo"><Shield size={23} /></div>
    <p className="auth-eyebrow">AI SECURITY GATEWAY</p>
    <h1>{isRegister ? "Create your account" : "Welcome back"}</h1>
    <p className="auth-subtitle">{isRegister ? "Set up your AgentGuard workspace." : "Sign in to your AgentGuard workspace."}</p>
    <form onSubmit={handleSubmit}>
      <label htmlFor="username">Username</label>
      <input id="username" value={username} onChange={(e) => setUsername(e.target.value)} minLength={3} maxLength={50} required autoComplete="username" placeholder="Enter your username" />
      {isRegister && <><label htmlFor="email">Email address</label><input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email" placeholder="you@example.com" /></>}
      <label htmlFor="password">Password</label>
      <input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} minLength={8} maxLength={128} required autoComplete={isRegister ? "new-password" : "current-password"} placeholder="Enter your password" />
      {error && <div className="auth-error" role="alert">{error}</div>}
      <button className="auth-submit" disabled={loading}>{loading ? "Please wait…" : isRegister ? "Create account" : "Sign in"}</button>
    </form>
    <div className="auth-switch">{isRegister ? "Already have an account?" : "New to AgentGuard?"}<button type="button" onClick={() => { setIsRegister(!isRegister); setError(""); }}>{isRegister ? "Sign in" : "Create account"}</button></div>
    <p className="auth-footer">AgentGuard AI · Protecting AI interactions</p>
  </section></main>;
}

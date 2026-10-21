import { useState } from "react";
import { Activity, Code2, Shield, ShieldCheck } from "lucide-react";
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
    <p className="auth-subtitle">{isRegister ? "Create a workspace to test prompts, set security policies, and review gateway decisions." : "Sign in to inspect AI requests, manage security policies, and review your audit trail."}</p>
    <div className="auth-benefits"><div><ShieldCheck size={15} /><span>Inspect prompts and sensitive data</span></div><div><Activity size={15} /><span>Apply policies and review decisions</span></div><div><Code2 size={15} /><span>Start in the browser; integrate by API later</span></div></div>
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
    <p className="auth-footer">AgentGuard AI · Inspect prompts and tool requests before they reach your AI provider.</p>
  </section></main>;
}

import { useState } from "react";
import { Activity, ArrowDown, ArrowUpRight, Check, Code2, LockKeyhole, Shield, ShieldCheck, Sparkles } from "lucide-react";
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

  return <main className="auth-page">
    <div className="auth-frame">
      <header className="auth-brandbar">
        <a className="auth-brand" href="/" aria-label="AgentGuard AI home">
          <span className="auth-logo"><Shield size={21} /></span>
          <span><strong>AgentGuard<span>AI</span></strong><small>SECURITY GATEWAY</small></span>
        </a>
        <div className="auth-secure-note"><LockKeyhole size={13} /> PRIVATE BY DESIGN</div>
      </header>

      <div className="auth-layout">
        <section className="auth-story">
          <div className="auth-live-pill"><span /> YOUR AI, WITH A SAFER WAY FORWARD</div>
          <h1>{isRegister ? <>Build with<br /><em>confidence.</em></> : <>Let your agents<br />think <em>boldly.</em></>}</h1>
          <p className="auth-story-copy">Put a thoughtful security layer between your AI and the actions that matter. Inspect requests, apply your rules, and keep a clear record of every decision.</p>

          <div className="auth-visual" aria-label="Illustration of an AI request being checked by AgentGuard">
            <div className="auth-visual-top"><span><i /> LIVE REQUEST PATH</span><span className="auth-visual-id">AG / 001</span></div>
            <div className="auth-flow">
              <div className="auth-flow-node"><span className="auth-node-icon"><Sparkles size={16} /></span><span><strong>AI agent</strong><small>Request received</small></span></div>
              <span className="auth-flow-line"><ArrowDown size={14} /></span>
              <div className="auth-inspection"><div><span className="auth-inspection-icon"><ShieldCheck size={17} /></span><span><strong>AgentGuard check</strong><small>Policy · privacy · risk</small></span><span className="auth-pass"><Check size={13} /> CLEAR</span></div><div className="auth-signal"><i /><i /><i /><i /><i /><span>All checks complete</span></div></div>
              <span className="auth-flow-line"><ArrowDown size={14} /></span>
              <div className="auth-flow-node auth-provider-node"><span className="auth-provider-mark"><Activity size={15} /></span><span><strong>Your model</strong><small>Only approved requests pass</small></span><ArrowUpRight size={14} /></div>
            </div>
            <div className="auth-visual-foot"><span>INPUT INSPECTED</span><span>POLICY APPLIED</span><span>DECISION RECORDED</span></div>
          </div>

          <div className="auth-proof-row">
            <div><ShieldCheck size={16} /><span><strong>Inspect</strong><small>Prompts & sensitive data</small></span></div>
            <div><Activity size={16} /><span><strong>Control</strong><small>Policies & action checks</small></span></div>
            <div><Code2 size={16} /><span><strong>Understand</strong><small>Evidence & audit history</small></span></div>
          </div>
          <p className="auth-disclaimer">Your agent runtime must honor gateway decisions. AgentGuard never executes approved tools for you.</p>
        </section>

        <section className="auth-card">
          <div className="auth-card-top"><span className="auth-card-kicker">{isRegister ? "A BETTER PLACE TO BUILD" : "GOOD TO SEE YOU AGAIN"}</span><span className="auth-card-spark"><Sparkles size={16} /></span></div>
          <h2>{isRegister ? "Create your workspace" : "Welcome back"}</h2>
          <p className="auth-subtitle">{isRegister ? "Start exploring safer AI workflows in just a moment." : "Sign in to your security workspace."}</p>
          <form onSubmit={handleSubmit}>
            <label htmlFor="username">Username or email</label>
            <input id="username" value={username} onChange={(e) => setUsername(e.target.value)} minLength={3} maxLength={254} required autoComplete="username" placeholder="you or your username" />
            {isRegister && <><label htmlFor="email">Email address</label><input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email" placeholder="you@example.com" /></>}
            <label htmlFor="password">Password</label>
            <input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} minLength={8} maxLength={128} required autoComplete={isRegister ? "new-password" : "current-password"} placeholder={isRegister ? "At least 8 characters" : "Enter your password"} />
            {error && <div className="auth-error" role="alert">{error}</div>}
            <button className="auth-submit" disabled={loading}>{loading ? "Please wait…" : isRegister ? "Create my account" : "Sign in to AgentGuard"}<ArrowUpRight size={16} /></button>
          </form>
          <div className="auth-switch">{isRegister ? "Already have an account?" : "New to AgentGuard?"}<button type="button" onClick={() => { setIsRegister(!isRegister); setError(""); }}>{isRegister ? "Sign in" : "Create account"}</button></div>
          <div className="auth-card-foot"><LockKeyhole size={13} /><span>Your credentials are protected in transit.</span></div>
        </section>
      </div>
      <footer className="auth-bottom"><span>AGENTGUARD AI <i /> BUILT FOR THE NEXT GENERATION OF AI</span><span>Keep the intelligence. Add the guardrails.</span></footer>
    </div>
  </main>;
}

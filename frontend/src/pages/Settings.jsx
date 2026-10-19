import { useEffect, useState } from "react";
import {
  Settings as SettingsIcon,
  Server,
  ShieldCheck,
  RefreshCw,
  CheckCircle,
  XCircle,
  Info,
} from "lucide-react";
import { getBackendHealth } from "../services/api";

const API_BASE_URL = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8001").replace(/\/$/, "");

export default function Settings() {
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastChecked, setLastChecked] = useState(null);

  async function checkBackend() {
    setLoading(true);

    try {
      const data = await getBackendHealth();
      setHealth(data);
    } catch {
      setHealth(null);
    } finally {
      setLoading(false);
      setLastChecked(new Date());
    }
  }

  useEffect(() => {
    checkBackend();
  }, []);

  const connected = health?.status === "healthy";

  return (
    <div className="min-h-screen bg-slate-950 p-6 text-white md:p-8">
      <div className="mx-auto max-w-5xl">
        <div className="mb-8">
          <p className="mb-2 text-sm text-purple-400">
            PLATFORM CONFIGURATION
          </p>
          <h1 className="text-3xl font-bold">Settings</h1>
          <p className="mt-2 text-slate-400">
            Monitor your AgentGuard AI configuration and service health.
          </p>
        </div>

        <div className="mb-6 rounded-2xl border border-slate-800 bg-slate-900 p-6">
          <div className="mb-5 flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <Server className="text-purple-400" size={24} />
              <div>
                <h2 className="text-lg font-semibold">
                  Backend Connection
                </h2>
                <p className="text-sm text-slate-400">
                  FastAPI service health
                </p>
              </div>
            </div>

            <button
              onClick={checkBackend}
              disabled={loading}
              className="flex items-center gap-2 rounded-xl border border-slate-700 px-4 py-2 hover:border-purple-500 disabled:opacity-50"
            >
              <RefreshCw size={16} />
              Refresh
            </button>
          </div>

          <div className="flex items-center gap-3 rounded-xl bg-slate-950 p-4">
            {loading ? (
              <>
                <RefreshCw
                  size={22}
                  className="animate-spin text-purple-400"
                />
                <span>Checking backend...</span>
              </>
            ) : connected ? (
              <>
                <CheckCircle size={22} className="text-emerald-400" />
                <div>
                  <p className="font-semibold text-emerald-400">
                    Backend Connected
                  </p>
                  <p className="text-sm text-slate-400">
                    {health.message || "Health endpoint responded successfully."}
                  </p>
                </div>
              </>
            ) : (
              <>
                <XCircle size={22} className="text-red-400" />
                <div>
                  <p className="font-semibold text-red-400">
                    Backend Unavailable
                  </p>
                  <p className="text-sm text-slate-400">
                    Start the FastAPI server and refresh this status.
                  </p>
                </div>
              </>
            )}
          </div>

          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <div className="rounded-xl border border-slate-800 p-4">
              <p className="text-sm text-slate-400">Backend URL</p>
              <p className="mt-2 break-all font-mono text-sm">
                {API_BASE_URL}
              </p>
            </div>

            <div className="rounded-xl border border-slate-800 p-4">
              <p className="text-sm text-slate-400">Last Checked</p>
              <p className="mt-2 text-sm">
                {lastChecked ? lastChecked.toLocaleString() : "Not checked"}
              </p>
            </div>
          </div>
        </div>

        <div className="mb-6 rounded-2xl border border-slate-800 bg-slate-900 p-6">
          <div className="mb-5 flex items-center gap-3">
            <ShieldCheck className="text-purple-400" size={24} />
            <div>
              <h2 className="text-lg font-semibold">
                Security Configuration
              </h2>
              <p className="text-sm text-slate-400">
                Current platform capabilities
              </p>
            </div>
          </div>

          <div className="space-y-3">
            {[
              {
                title: "Prompt Injection Detection",
                description: "Inspect incoming prompts for suspicious instructions.",
              },
              {
                title: "PII Detection",
                description: "Identify common personal data and secret patterns.",
              },
              {
                title: "Risk Scoring",
                description: "Assign risk scores using the configured detector.",
              },
              {
                title: "Security Event Logging",
                description: "Store request outcomes in the backend database.",
              },
              {
                title: "AI Provider Integration",
                description: "Send permitted prompts to the configured backend AI provider.",
              },
            ].map((item) => (
              <div
                key={item.title}
                className="flex items-start gap-3 rounded-xl border border-slate-800 p-4"
              >
                <ShieldCheck
                  size={19}
                  className="mt-0.5 text-purple-400"
                />
                <div>
                  <p className="font-medium">{item.title}</p>
                  <p className="mt-1 text-sm text-slate-400">
                    {item.description}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-2xl border border-purple-500/20 bg-purple-500/5 p-5">
          <div className="flex items-start gap-3">
            <Info size={21} className="mt-0.5 text-purple-400" />
            <div>
              <h3 className="font-semibold">API Key Security</h3>
              <p className="mt-2 text-sm leading-6 text-slate-400">
                Keep your Groq API key inside backend/.env. Never place
                provider credentials in React code or expose them in
                browser requests. The frontend should communicate only
                with your backend gateway.
              </p>
            </div>
          </div>
        </div>

        <div className="mt-6 flex items-center gap-3 text-slate-500">
          <SettingsIcon size={17} />
          <span className="text-sm">AgentGuard AI · Configuration Center</span>
        </div>
      </div>
    </div>
  );
}

import { useState } from "react";
import axios from "axios";
import {
  ShieldCheck,
  ShieldAlert,
  Loader2,
  Send,
  RotateCcw,
} from "lucide-react";

const API = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8001").replace(/\/$/, "");

export default function Playground() {
  const [prompt, setPrompt] = useState("");
  const [useAI, setUseAI] = useState(true);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  async function scanPrompt() {
    if (!prompt.trim()) return;

    setLoading(true);
    setResult(null);
    setError("");

    try {
      const response = await axios.post(`${API}/gateway/scan`, {
        prompt: prompt.trim(),
        use_ai: useAI,
      });

      setResult(response.data);
    } catch (err) {
      setError(
        err.response?.data?.detail?.message ||
        err.response?.data?.detail ||
        "Request failed. Check the backend connection."
      );
    } finally {
      setLoading(false);
    }
  }

  function reset() {
    setPrompt("");
    setResult(null);
    setError("");
  }

  const blocked = result?.blocked;

  return (
    <div className="min-h-screen bg-slate-950 p-6 text-white md:p-8">
      <div className="mx-auto max-w-6xl">
        <div className="mb-8">
          <p className="mb-2 text-sm text-purple-400">
            INTERACTIVE SECURITY LAB
          </p>
          <h1 className="text-3xl font-bold">AI Security Playground</h1>
          <p className="mt-2 text-slate-400">
            Inspect prompts, evaluate risks and examine AI responses.
          </p>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <section className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
            <label className="mb-3 block font-semibold">
              Enter your prompt
            </label>

            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              maxLength={10000}
              placeholder="Example: Explain how neural networks learn..."
              className="h-64 w-full resize-y rounded-xl border border-slate-700 bg-slate-950 p-4 text-white outline-none placeholder:text-slate-600 focus:border-purple-500"
            />

            <div className="mt-2 text-right text-xs text-slate-500">
              {prompt.length}/10000
            </div>

            <label className="mt-4 flex cursor-pointer items-center gap-3">
              <input
                type="checkbox"
                checked={useAI}
                onChange={(e) => setUseAI(e.target.checked)}
                className="accent-purple-500"
              />
              <span className="text-sm text-slate-300">
                Generate an AI response using Groq
              </span>
            </label>

            <div className="mt-6 flex flex-wrap gap-3">
              <button
                onClick={scanPrompt}
                disabled={loading || !prompt.trim()}
                className="flex items-center gap-2 rounded-xl bg-purple-600 px-5 py-3 font-semibold hover:bg-purple-500 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {loading ? (
                  <Loader2 size={18} className="animate-spin" />
                ) : (
                  <Send size={18} />
                )}
                {loading ? "Scanning..." : "Scan Prompt"}
              </button>

              <button
                onClick={reset}
                className="flex items-center gap-2 rounded-xl border border-slate-700 px-5 py-3 hover:bg-slate-800"
              >
                <RotateCcw size={17} />
                Reset
              </button>
            </div>

            {error && (
              <div className="mt-5 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300">
                {typeof error === "string"
                  ? error
                  : JSON.stringify(error)}
              </div>
            )}
          </section>

          <section className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
            <h2 className="mb-5 text-xl font-semibold">
              Security Analysis
            </h2>

            {!result && !loading && (
              <div className="flex min-h-64 flex-col items-center justify-center text-center">
                <ShieldCheck size={48} className="mb-4 text-slate-600" />
                <p className="text-slate-300">Ready to analyze</p>
                <p className="mt-2 text-sm text-slate-500">
                  Submit a prompt to see the security assessment.
                </p>
              </div>
            )}

            {loading && (
              <div className="flex min-h-64 flex-col items-center justify-center">
                <Loader2
                  size={38}
                  className="animate-spin text-purple-400"
                />
                <p className="mt-4 text-slate-400">
                  Analyzing prompt...
                </p>
              </div>
            )}

            {result && (
              <div className="space-y-5">
                <div
                  className={`rounded-xl border p-4 ${
                    blocked
                      ? "border-red-500/30 bg-red-500/10"
                      : result.status === "FLAGGED"
                        ? "border-amber-500/30 bg-amber-500/10"
                        : "border-emerald-500/30 bg-emerald-500/10"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    {blocked ? (
                      <ShieldAlert className="text-red-400" size={28} />
                    ) : (
                      <ShieldCheck className="text-emerald-400" size={28} />
                    )}

                    <div>
                      <p className="font-bold">{result.status}</p>
                      <p className="text-sm text-slate-400">
                        Event ID: {result.event_id ?? "Unavailable"}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="rounded-xl border border-slate-800 p-4">
                    <p className="text-sm text-slate-400">Risk Score</p>
                    <p className="mt-2 text-3xl font-bold">
                      {result.risk_score ?? 0}
                      <span className="text-sm text-slate-500">/100</span>
                    </p>
                  </div>

                  <div className="rounded-xl border border-slate-800 p-4">
                    <p className="text-sm text-slate-400">Risk Level</p>
                    <p className="mt-2 text-2xl font-bold">
                      {result.risk_level ?? "UNKNOWN"}
                    </p>
                  </div>
                </div>

                <div>
                  <p className="mb-2 font-semibold">PII Detection</p>
                  <p className="text-sm text-slate-400">
                    {result.pii_detected
                      ? `Detected: ${(result.pii_types || []).join(", ")}`
                      : "No PII detected by the scanner."}
                  </p>
                </div>

                {result.detection_reasons?.length > 0 && (
                  <div>
                    <p className="mb-2 font-semibold">Detection Reasons</p>
                    <ul className="list-inside list-disc space-y-1 text-sm text-slate-400">
                      {result.detection_reasons.map((reason, index) => (
                        <li key={index}>{reason}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {result.policy_reasons?.length > 0 && (
                  <div>
                    <p className="mb-2 font-semibold">Policy Reasons</p>
                    <ul className="list-inside list-disc space-y-1 text-sm text-red-300">
                      {result.policy_reasons.map((reason, index) => (
                        <li key={index}>{reason}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {result.ai_response && (
                  <div>
                    <p className="mb-2 font-semibold">AI Response</p>
                    <div className="whitespace-pre-wrap rounded-xl border border-slate-800 bg-slate-950 p-4 text-sm leading-6 text-slate-300">
                      {result.ai_response}
                    </div>
                    {result.ai_model && (
                      <p className="mt-2 text-xs text-slate-500">
                        Model: {result.ai_model}
                      </p>
                    )}
                  </div>
                )}

                {result.output_scan && (
                  <div>
                    <p className="mb-2 font-semibold">Output Scan</p>
                    <p className="text-sm text-slate-400">
                      Risk: {result.output_scan.risk_score} ·{" "}
                      {result.output_scan.risk_level}
                    </p>
                    {result.output_scan.reasons?.map((reason, index) => (
                      <p key={index} className="mt-1 text-sm text-amber-300">
                        {reason}
                      </p>
                    ))}
                  </div>
                )}

                {result.prompt_redacted && (
                  <p className="text-sm text-amber-300">
                    Sensitive values were redacted before processing.
                  </p>
                )}
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}

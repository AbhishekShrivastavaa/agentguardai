import { useEffect, useState } from "react";
import {
  ShieldCheck,
  Plus,
  Trash2,
  RefreshCw,
  ShieldAlert,
} from "lucide-react";
import {
  getPolicies,
  createPolicy,
  updatePolicy,
  deletePolicy,
} from "../services/api";

const inputStyle =
  "w-full rounded-xl border border-slate-700 bg-slate-950 p-3 text-white outline-none focus:border-purple-500";

export default function Policies() {
  const [policies, setPolicies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const [form, setForm] = useState({
    name: "",
    description: "",
    action: "block",
    risk_threshold: 70,
    enabled: true,
  });

  async function loadPolicies() {
    setLoading(true);
    setError("");

    try {
      const data = await getPolicies();
      setPolicies(Array.isArray(data) ? data : data.policies || []);
    } catch (err) {
      setError(err.message || "Unable to load policies.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadPolicies();
  }, []);

  async function handleCreate(e) {
    e.preventDefault();
    setSaving(true);
    setError("");

    try {
      await createPolicy({
        ...form,
        risk_threshold: Number(form.risk_threshold),
      });

      setForm({
        name: "",
        description: "",
        action: "block",
        risk_threshold: 70,
        enabled: true,
      });

      await loadPolicies();
    } catch (err) {
      setError(err.message || "Unable to create policy.");
    } finally {
      setSaving(false);
    }
  }

  async function togglePolicy(policy) {
    setError("");

    try {
      await updatePolicy(policy.id, {
        enabled: !policy.enabled,
        action: policy.action,
        risk_threshold: Number(policy.risk_threshold),
      });

      await loadPolicies();
    } catch (err) {
      setError(err.message || "Unable to update policy.");
    }
  }

  async function removePolicy(policy) {
    if (!window.confirm(`Delete policy "${policy.name}"?`)) return;

    setError("");

    try {
      await deletePolicy(policy.id);
      await loadPolicies();
    } catch (err) {
      setError(err.message || "Unable to delete policy.");
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 p-6 text-white md:p-8">
      <div className="mx-auto max-w-7xl">
        <div className="mb-8 flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="mb-2 text-sm text-purple-400">
              SECURITY CONFIGURATION
            </p>
            <h1 className="text-3xl font-bold">Security Policies</h1>
            <p className="mt-2 text-slate-400">
              Configure how AgentGuard AI handles detected threats.
            </p>
          </div>

          <button
            onClick={loadPolicies}
            disabled={loading}
            className="flex items-center gap-2 rounded-xl border border-slate-700 px-4 py-3 hover:border-purple-500"
          >
            <RefreshCw size={17} />
            Refresh
          </button>
        </div>

        {error && (
          <div className="mb-6 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-red-300">
            {error}
          </div>
        )}

        <div className="grid gap-6 lg:grid-cols-3">
          <form
            onSubmit={handleCreate}
            className="h-fit rounded-2xl border border-slate-800 bg-slate-900 p-6 lg:col-span-1"
          >
            <div className="mb-5 flex items-center gap-3">
              <Plus className="text-purple-400" />
              <h2 className="text-xl font-semibold">Create Policy</h2>
            </div>

            <label className="mb-2 block text-sm text-slate-300">
              Policy Name
            </label>
            <input
              required
              minLength={1}
              maxLength={100}
              value={form.name}
              onChange={(e) =>
                setForm({ ...form, name: e.target.value })
              }
              placeholder="e.g. Block sensitive data"
              className={`${inputStyle} mb-4`}
            />

            <label className="mb-2 block text-sm text-slate-300">
              Description
            </label>
            <textarea
              maxLength={1000}
              value={form.description}
              onChange={(e) =>
                setForm({ ...form, description: e.target.value })
              }
              placeholder="Describe this security rule..."
              className={`${inputStyle} mb-4 h-24`}
            />

            <label className="mb-2 block text-sm text-slate-300">
              Action
            </label>
            <select
              value={form.action}
              onChange={(e) =>
                setForm({ ...form, action: e.target.value })
              }
              className={`${inputStyle} mb-4`}
            >
              <option value="block">Block</option>
              <option value="flag">Flag</option>
              <option value="redact">Redact</option>
              <option value="allow">Allow</option>
            </select>

            <label className="mb-2 block text-sm text-slate-300">
              Risk Threshold: {form.risk_threshold}
            </label>
            <input
              type="range"
              min="0"
              max="100"
              value={form.risk_threshold}
              onChange={(e) =>
                setForm({
                  ...form,
                  risk_threshold: Number(e.target.value),
                })
              }
              className="mb-5 w-full accent-purple-500"
            />

            <label className="mb-5 flex items-center gap-3 text-sm text-slate-300">
              <input
                type="checkbox"
                checked={form.enabled}
                onChange={(e) =>
                  setForm({ ...form, enabled: e.target.checked })
                }
                className="accent-purple-500"
              />
              Enable policy immediately
            </label>

            <button
              type="submit"
              disabled={saving}
              className="w-full rounded-xl bg-purple-600 p-3 font-semibold hover:bg-purple-500 disabled:opacity-50"
            >
              {saving ? "Creating..." : "Create Policy"}
            </button>
          </form>

          <section className="rounded-2xl border border-slate-800 bg-slate-900 p-6 lg:col-span-2">
            <div className="mb-5 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <ShieldCheck className="text-purple-400" />
                <h2 className="text-xl font-semibold">Active Policies</h2>
              </div>
              <span className="rounded-full bg-slate-800 px-3 py-1 text-sm">
                {policies.filter((p) => p.enabled).length} enabled
              </span>
            </div>

            {loading ? (
              <p className="py-10 text-center text-slate-400">
                Loading policies...
              </p>
            ) : policies.length === 0 ? (
              <div className="py-12 text-center">
                <ShieldAlert
                  size={40}
                  className="mx-auto mb-3 text-slate-600"
                />
                <p className="text-slate-300">No policies found.</p>
                <p className="mt-2 text-sm text-slate-500">
                  Create a policy using the form.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {policies.map((policy) => (
                  <article
                    key={policy.id}
                    className="rounded-xl border border-slate-800 bg-slate-950 p-5"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-4">
                      <div>
                        <h3 className="font-semibold">{policy.name}</h3>
                        <p className="mt-2 text-sm text-slate-400">
                          {policy.description || "No description provided."}
                        </p>
                      </div>

                      <span
                        className={`rounded-full px-3 py-1 text-xs ${
                          policy.enabled
                            ? "bg-emerald-500/15 text-emerald-400"
                            : "bg-slate-800 text-slate-400"
                        }`}
                      >
                        {policy.enabled ? "ENABLED" : "DISABLED"}
                      </span>
                    </div>

                    <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-slate-800 pt-4">
                      <div className="flex flex-wrap gap-3 text-sm">
                        <span className="rounded-lg bg-slate-800 px-3 py-2">
                          Action: {policy.action?.toUpperCase()}
                        </span>
                        <span className="rounded-lg bg-slate-800 px-3 py-2">
                          Threshold: {policy.risk_threshold}
                        </span>
                      </div>

                      <div className="flex gap-2">
                        <button
                          onClick={() => togglePolicy(policy)}
                          className="rounded-lg border border-slate-700 px-3 py-2 text-sm hover:border-purple-500"
                        >
                          {policy.enabled ? "Disable" : "Enable"}
                        </button>

                        <button
                          onClick={() => removePolicy(policy)}
                          aria-label={`Delete ${policy.name}`}
                          className="rounded-lg border border-red-500/30 p-2 text-red-400 hover:bg-red-500/10"
                        >
                          <Trash2 size={17} />
                        </button>
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
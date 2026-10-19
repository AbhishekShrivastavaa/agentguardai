import { useEffect, useState } from "react";
import axios from "axios";
import {
  ShieldCheck,
  ShieldAlert,
  Activity,
  AlertTriangle,
  RefreshCw,
} from "lucide-react";

const API = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8001").replace(/\/$/, "");

export default function Dashboard() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function fetchDashboard() {
    setLoading(true);
    setError("");

    try {
      const response = await axios.get(`${API}/events/`);
      setEvents(response.data.events || []);
    } catch {
      setError("Unable to connect to the backend.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchDashboard();
  }, []);

  const blocked = events.filter(
    (event) =>
      event.status === "BLOCKED" ||
      event.status === "OUTPUT_BLOCKED"
  ).length;

  const flagged = events.filter(
    (event) => event.status === "FLAGGED"
  ).length;

  const averageRisk = events.length
    ? Math.round(
        events.reduce(
          (sum, event) => sum + Number(event.risk_score || 0),
          0
        ) / events.length
      )
    : 0;

  const stats = [
    {
      label: "Total Security Events",
      value: events.length,
      icon: Activity,
    },
    {
      label: "Blocked Requests",
      value: blocked,
      icon: ShieldAlert,
    },
    {
      label: "Flagged Requests",
      value: flagged,
      icon: AlertTriangle,
    },
    {
      label: "Average Risk Score",
      value: `${averageRisk}/100`,
      icon: ShieldCheck,
    },
  ];

  return (
    <div className="min-h-screen bg-slate-950 p-6 text-white md:p-8">
      <div className="mx-auto max-w-7xl">
        <div className="mb-8 flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="mb-2 text-sm text-purple-400">
              AI SECURITY PLATFORM
            </p>

            <h1 className="text-3xl font-bold">
              Security Dashboard
            </h1>

            <p className="mt-2 text-slate-400">
              Monitor AI threats and security events.
            </p>
          </div>

          <button
            onClick={fetchDashboard}
            disabled={loading}
            className="flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 hover:border-purple-500 disabled:opacity-50"
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

        <div className="mb-8 grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
          {stats.map((stat) => {
            const Icon = stat.icon;

            return (
              <div
                key={stat.label}
                className="rounded-2xl border border-slate-800 bg-slate-900 p-6"
              >
                <div className="mb-5 flex items-center justify-between">
                  <span className="text-sm text-slate-400">
                    {stat.label}
                  </span>

                  <Icon className="text-purple-400" size={22} />
                </div>

                <p className="text-3xl font-bold">
                  {loading ? "..." : stat.value}
                </p>
              </div>
            );
          })}
        </div>

        <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900">
          <div className="border-b border-slate-800 p-6">
            <h2 className="text-xl font-semibold">
              Recent Security Events
            </h2>

            <p className="mt-1 text-sm text-slate-400">
              Events retrieved from the backend database.
            </p>
          </div>

          {loading ? (
            <p className="p-6 text-slate-400">
              Loading security events...
            </p>
          ) : events.length === 0 ? (
            <p className="p-6 text-slate-400">
              No security events recorded yet.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-800/60 text-slate-400">
                  <tr>
                    <th className="p-4">ID</th>
                    <th className="p-4">Prompt</th>
                    <th className="p-4">Status</th>
                    <th className="p-4">Risk Score</th>
                    <th className="p-4">Risk Level</th>
                  </tr>
                </thead>

                <tbody>
                  {events.slice(0, 10).map((event) => (
                    <tr
                      key={event.id}
                      className="border-t border-slate-800"
                    >
                      <td className="p-4 text-slate-400">
                        #{event.id}
                      </td>

                      <td className="max-w-xs truncate p-4">
                        {event.prompt || "—"}
                      </td>

                      <td className="p-4">
                        <span
                          className={`rounded-full px-3 py-1 text-xs font-semibold ${
                            event.status === "BLOCKED" ||
                            event.status === "OUTPUT_BLOCKED"
                              ? "bg-red-500/15 text-red-400"
                              : event.status === "FLAGGED"
                                ? "bg-amber-500/15 text-amber-400"
                                : "bg-emerald-500/15 text-emerald-400"
                          }`}
                        >
                          {event.status}
                        </span>
                      </td>

                      <td className="p-4">
                        {event.risk_score}/100
                      </td>

                      <td className="p-4 text-slate-300">
                        {event.risk_level || "UNKNOWN"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

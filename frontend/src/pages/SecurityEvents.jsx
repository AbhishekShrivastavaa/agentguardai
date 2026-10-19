import { useEffect, useMemo, useState } from "react";
import { getSecurityEvents } from "../services/api";
import {
  RefreshCw,
  Search,
  ShieldAlert,
  Activity,
  X,
  Clock,
} from "lucide-react";

export default function SecurityEvents() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("ALL");
  const [selected, setSelected] = useState(null);

  async function loadEvents() {
    setLoading(true);
    setError("");

    try {
      const data = await getSecurityEvents();
      setEvents(data.events || []);
    } catch (err) {
      setError(err.message || "Unable to load security events.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadEvents();
  }, []);

  const filteredEvents = useMemo(() => {
    return events.filter((event) => {
      const matchesSearch = [
        event.prompt,
        event.status,
        event.risk_level,
        ...(event.reasons || []),
      ]
        .join(" ")
        .toLowerCase()
        .includes(search.toLowerCase());

      const matchesFilter =
        filter === "ALL" || event.status === filter;

      return matchesSearch && matchesFilter;
    });
  }, [events, search, filter]);

  const blockedCount = events.filter((e) =>
    ["BLOCKED", "OUTPUT_BLOCKED"].includes(e.status)
  ).length;

  const flaggedCount = events.filter(
    (e) => e.status === "FLAGGED"
  ).length;

  function statusStyle(status) {
    if (["BLOCKED", "OUTPUT_BLOCKED"].includes(status)) {
      return "bg-red-500/15 text-red-400 border-red-500/20";
    }

    if (["FLAGGED", "AI_ERROR"].includes(status)) {
      return "bg-amber-500/15 text-amber-400 border-amber-500/20";
    }

    return "bg-emerald-500/15 text-emerald-400 border-emerald-500/20";
  }

  function riskStyle(score) {
    if (score >= 70) return "text-red-400";
    if (score >= 40) return "text-amber-400";
    return "text-emerald-400";
  }

  return (
    <div className="min-h-screen bg-slate-950 p-6 text-white md:p-8">
      <div className="mx-auto max-w-7xl">
        <div className="mb-8 flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="mb-2 text-sm text-purple-400">
              THREAT MONITORING
            </p>
            <h1 className="text-3xl font-bold">
              Security Events
            </h1>
            <p className="mt-2 text-slate-400">
              Investigate prompt scans and recorded security incidents.
            </p>
          </div>

          <button
            onClick={loadEvents}
            disabled={loading}
            className="flex items-center gap-2 rounded-xl border border-slate-700 px-4 py-3 hover:border-purple-500 disabled:opacity-50"
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

        <div className="mb-6 grid gap-4 sm:grid-cols-3">
          {[
            {
              label: "Total Events",
              value: events.length,
              icon: Activity,
            },
            {
              label: "Blocked Events",
              value: blockedCount,
              icon: ShieldAlert,
            },
            {
              label: "Flagged Events",
              value: flaggedCount,
              icon: Clock,
            },
          ].map((item) => {
            const Icon = item.icon;

            return (
              <div
                key={item.label}
                className="rounded-2xl border border-slate-800 bg-slate-900 p-5"
              >
                <div className="flex items-center justify-between">
                  <p className="text-sm text-slate-400">
                    {item.label}
                  </p>
                  <Icon size={21} className="text-purple-400" />
                </div>
                <p className="mt-3 text-3xl font-bold">
                  {loading ? "..." : item.value}
                </p>
              </div>
            );
          })}
        </div>

        <div className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900">
          <div className="flex flex-col gap-4 border-b border-slate-800 p-5 lg:flex-row">
            <div className="relative flex-1">
              <Search
                size={18}
                className="absolute left-3 top-3.5 text-slate-500"
              />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search prompts, status or reasons..."
                className="w-full rounded-xl border border-slate-700 bg-slate-950 py-3 pl-10 pr-4 text-white outline-none focus:border-purple-500"
              />
            </div>

            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none"
            >
              <option value="ALL">All statuses</option>
              <option value="ALLOWED">Allowed</option>
              <option value="BLOCKED">Blocked</option>
              <option value="OUTPUT_BLOCKED">Output blocked</option>
              <option value="FLAGGED">Flagged</option>
              <option value="AI_ERROR">AI errors</option>
            </select>
          </div>

          {loading ? (
            <p className="p-10 text-center text-slate-400">
              Loading security events...
            </p>
          ) : filteredEvents.length === 0 ? (
            <div className="p-12 text-center">
              <ShieldAlert
                size={38}
                className="mx-auto mb-3 text-slate-600"
              />
              <p className="text-slate-300">
                No matching events found.
              </p>
              <p className="mt-2 text-sm text-slate-500">
                Events will appear here when requests are processed.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-950 text-slate-400">
                  <tr>
                    <th className="p-4">Event</th>
                    <th className="p-4">Prompt</th>
                    <th className="p-4">Status</th>
                    <th className="p-4">Risk</th>
                    <th className="p-4">Timestamp</th>
                    <th className="p-4">Details</th>
                  </tr>
                </thead>

                <tbody>
                  {filteredEvents.map((event) => (
                    <tr
                      key={event.id}
                      className="border-t border-slate-800 hover:bg-slate-800/30"
                    >
                      <td className="p-4 text-slate-400">
                        #{event.id}
                      </td>

                      <td className="max-w-xs truncate p-4">
                        {event.prompt || "—"}
                      </td>

                      <td className="p-4">
                        <span
                          className={`whitespace-nowrap rounded-full border px-3 py-1 text-xs font-semibold ${statusStyle(event.status)}`}
                        >
                          {event.status}
                        </span>
                      </td>

                      <td className={`p-4 font-semibold ${riskStyle(Number(event.risk_score || 0))}`}>
                        {event.risk_score}/100
                        <div className="mt-1 text-xs text-slate-500">
                          {event.risk_level || "UNKNOWN"}
                        </div>
                      </td>

                      <td className="whitespace-nowrap p-4 text-slate-400">
                        {event.timestamp
                          ? new Date(event.timestamp).toLocaleString()
                          : "—"}
                      </td>

                      <td className="p-4">
                        <button
                          onClick={() => setSelected(event)}
                          className="rounded-lg border border-slate-700 px-3 py-2 hover:border-purple-500"
                        >
                          View
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="border-t border-slate-800 p-4 text-sm text-slate-500">
            Showing {filteredEvents.length} of {events.length} events
          </div>
        </div>

        {selected && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
            <div className="max-h-[85vh] w-full max-w-2xl overflow-y-auto rounded-2xl border border-slate-700 bg-slate-900 p-6">
              <div className="mb-5 flex items-center justify-between">
                <h2 className="text-xl font-bold">
                  Event #{selected.id}
                </h2>

                <button
                  onClick={() => setSelected(null)}
                  className="rounded-lg p-2 hover:bg-slate-800"
                  aria-label="Close event details"
                >
                  <X size={20} />
                </button>
              </div>

              <div className="space-y-5">
                <div>
                  <p className="mb-2 text-sm text-slate-400">Status</p>
                  <span
                    className={`rounded-full border px-3 py-1 text-xs ${statusStyle(selected.status)}`}
                  >
                    {selected.status}
                  </span>
                </div>

                <div>
                  <p className="mb-2 text-sm text-slate-400">
                    Recorded Prompt
                  </p>
                  <div className="whitespace-pre-wrap break-words rounded-xl bg-slate-950 p-4 text-sm">
                    {selected.prompt || "No prompt recorded."}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="rounded-xl bg-slate-950 p-4">
                    <p className="text-sm text-slate-400">Risk Score</p>
                    <p className={`mt-2 text-2xl font-bold ${riskStyle(Number(selected.risk_score || 0))}`}>
                      {selected.risk_score}/100
                    </p>
                  </div>

                  <div className="rounded-xl bg-slate-950 p-4">
                    <p className="text-sm text-slate-400">Risk Level</p>
                    <p className="mt-2 text-2xl font-bold">
                      {selected.risk_level || "UNKNOWN"}
                    </p>
                  </div>
                </div>

                <div>
                  <p className="mb-2 text-sm text-slate-400">
                    Detection Reasons
                  </p>
                  {selected.reasons?.length ? (
                    <ul className="list-inside list-disc space-y-2 text-sm text-slate-300">
                      {selected.reasons.map((reason, index) => (
                        <li key={index}>{reason}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-sm text-slate-500">
                      No reasons recorded for this event.
                    </p>
                  )}
                </div>

                <p className="text-xs text-slate-500">
                  Recorded:{" "}
                  {selected.timestamp
                    ? new Date(selected.timestamp).toLocaleString()
                    : "Timestamp unavailable"}
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import AuthGuard from "@/components/AuthGuard";
import { api, ApiError } from "@/lib/api";
import { IncidentListItem, AttemptPublic } from "@/lib/types";

const DIFFICULTY_COLOR: Record<string, string> = {
  Beginner: "text-signal-green border-signal-green/40 bg-signal-green/10",
  Intermediate: "text-signal-amber border-signal-amber/40 bg-signal-amber/10",
  Advanced: "text-signal-red border-signal-red/40 bg-signal-red/10",
};

export default function IncidentsPage() {
  const [incidents, setIncidents] = useState<IncidentListItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [starting, setStarting] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    api.get<IncidentListItem[]>("/incidents").then(setIncidents).catch((e) => setError(e.message));
  }, []);

  async function startIncident(incidentId: string) {
    setStarting(incidentId);
    setError(null);
    try {
      const attempt = await api.post<AttemptPublic>("/incidents/attempts", { incident_id: incidentId });
      router.push(`/incidents/${incidentId}?attempt=${attempt.id}`);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not start this incident.");
    } finally {
      setStarting(null);
    }
  }

  return (
    <AuthGuard>
      <h1 className="text-2xl font-semibold text-slate-100">Network Incidents</h1>
      <p className="mt-1 text-sm text-slate-500">
        Realistic NOC tickets. Investigate with the CLI, reason with the AI coach, and fix the root cause — not just
        the symptom.
      </p>

      {error && <p className="mt-4 text-sm text-signal-red">{error}</p>}

      <div className="mt-8 grid grid-cols-1 gap-4 md:grid-cols-2">
        {incidents.map((inc) => (
          <div key={inc.id} className="flex flex-col rounded-lg border border-ink-700 bg-ink-900 p-5">
            <div className="mb-2 flex items-center justify-between">
              <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${DIFFICULTY_COLOR[inc.difficulty] || ""}`}>
                {inc.difficulty}
              </span>
              <span className="font-mono text-xs text-slate-500">
                {inc.priority} · {inc.category}
              </span>
            </div>
            <h3 className="text-base font-semibold text-slate-100">{inc.title}</h3>
            <p className="mt-2 flex-1 text-sm text-slate-400">{inc.summary}</p>
            <div className="mt-4 flex items-center justify-between">
              <span className="text-xs text-accent-400">+{inc.xp_reward} XP</span>
              {!inc.is_free_tier && (
                <span className="rounded-full border border-slate-600 px-2 py-0.5 text-[10px] uppercase tracking-wide text-slate-400">
                  Pro
                </span>
              )}
            </div>
            <button
              onClick={() => startIncident(inc.id)}
              disabled={starting === inc.id}
              className="mt-4 w-full rounded-md bg-accent-500 px-4 py-2 text-sm font-semibold text-ink-950 hover:bg-accent-400 disabled:opacity-60"
            >
              {starting === inc.id ? "Starting…" : "Start Incident"}
            </button>
          </div>
        ))}
      </div>
    </AuthGuard>
  );
}

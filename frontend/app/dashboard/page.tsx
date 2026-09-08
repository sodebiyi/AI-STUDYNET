"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import AuthGuard from "@/components/AuthGuard";
import { api } from "@/lib/api";
import { DashboardSummary } from "@/lib/types";

function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-lg border border-ink-700 bg-ink-900 p-5">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-slate-100">{value}</p>
      {sub && <p className="mt-1 text-xs text-slate-500">{sub}</p>}
    </div>
  );
}

function ProgressBar({ value }: { value: number }) {
  const color = value >= 75 ? "bg-signal-green" : value >= 50 ? "bg-signal-amber" : "bg-signal-red";
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-ink-800">
      <div className={`h-full ${color} transition-all`} style={{ width: `${Math.min(100, Math.max(0, value))}%` }} />
    </div>
  );
}

function formatSeconds(s: number | null): string {
  if (s === null) return "—";
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return `${m}m ${sec}s`;
}

export default function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<DashboardSummary>("/dashboard")
      .then(setSummary)
      .catch((e) => setError(e.message));
  }, []);

  return (
    <AuthGuard>
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-slate-100">
          Welcome back{summary ? `, ${summary.display_name}` : ""}
        </h1>
        <p className="mt-1 text-sm text-slate-500">Here&rsquo;s where you stand as a Network Engineer.</p>
      </div>

      {error && <p className="text-sm text-signal-red">{error}</p>}

      {summary && (
        <>
          <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
            <StatCard label="Network Engineer Level" value={summary.skill_level} />
            <StatCard label="Overall Skill" value={`${summary.overall_skill_percent}%`} />
            <StatCard label="Troubleshooting Score" value={`${summary.troubleshooting_score_percent}%`} />
            <StatCard label="XP" value={summary.xp.toLocaleString()} sub={`${summary.current_streak_days}-day streak`} />
            <StatCard label="Incidents Solved" value={`${summary.incidents_solved} / ${summary.incidents_completed}`} />
            <StatCard label="Avg. Resolution Time" value={formatSeconds(summary.average_resolution_seconds)} />
            <StatCard label="Hints Used" value={`${summary.hints_used_total}`} />
            <StatCard label="Strongest Skill" value={summary.strongest_skill || "—"} />
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <div className="rounded-lg border border-ink-700 bg-ink-900 p-5 lg:col-span-2">
              <p className="text-xs uppercase tracking-wide text-slate-500">Overall skill progress</p>
              <div className="mt-3">
                <ProgressBar value={summary.overall_skill_percent} />
              </div>
              {summary.weakest_skill && (
                <p className="mt-3 text-sm text-slate-400">
                  Weakest area right now: <span className="text-signal-amber">{summary.weakest_skill}</span>
                </p>
              )}
            </div>
            <div className="rounded-lg border border-accent-500/30 bg-accent-500/5 p-5">
              <p className="text-xs uppercase tracking-wide text-accent-400">Recommended next</p>
              <p className="mt-2 text-lg font-medium text-slate-100">{summary.recommended_next}</p>
              <Link
                href="/incidents"
                className="mt-4 inline-block rounded-md bg-accent-500 px-4 py-2 text-xs font-semibold text-ink-950 hover:bg-accent-400"
              >
                Go to incidents
              </Link>
            </div>
          </div>

          <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
            <Link href="/packet-visualiser" className="rounded-lg border border-ink-700 bg-ink-900 p-5 hover:border-accent-500/50">
              <h3 className="text-sm font-semibold text-slate-100">Follow the Packet</h3>
              <p className="mt-1 text-xs text-slate-500">Visualise how traffic actually flows through the network.</p>
            </Link>
            <Link href="/incidents" className="rounded-lg border border-ink-700 bg-ink-900 p-5 hover:border-accent-500/50">
              <h3 className="text-sm font-semibold text-slate-100">Network Incidents</h3>
              <p className="mt-1 text-xs text-slate-500">Investigate realistic NOC tickets with the AI coach.</p>
            </Link>
            <Link href="/readiness" className="rounded-lg border border-ink-700 bg-ink-900 p-5 hover:border-accent-500/50">
              <h3 className="text-sm font-semibold text-slate-100">Am I Job Ready?</h3>
              <p className="mt-1 text-xs text-slate-500">See your full Network Engineer readiness report.</p>
            </Link>
          </div>
        </>
      )}
    </AuthGuard>
  );
}

"use client";

import { useEffect, useState } from "react";
import AuthGuard from "@/components/AuthGuard";
import { api } from "@/lib/api";
import { ReadinessReport } from "@/lib/types";

const SKILL_LABELS: [keyof ReadinessReport, string][] = [
  ["fundamentals", "Fundamentals"],
  ["layer1", "Layer 1"],
  ["layer2_switching", "Switching"],
  ["layer3_routing", "Routing"],
  ["network_services", "Network Services"],
  ["security", "Security"],
  ["monitoring", "Monitoring"],
  ["troubleshooting_methodology", "Troubleshooting"],
  ["communication", "Communication"],
];

function barColor(value: number) {
  if (value >= 75) return "bg-signal-green";
  if (value >= 50) return "bg-signal-amber";
  return "bg-signal-red";
}

export default function ReadinessPage() {
  const [report, setReport] = useState<ReadinessReport | null>(null);

  useEffect(() => {
    api.get<ReadinessReport>("/readiness").then(setReport).catch(() => {});
  }, []);

  return (
    <AuthGuard>
      <h1 className="text-2xl font-semibold text-slate-100">Am I Job Ready?</h1>
      <p className="mt-1 text-sm text-slate-500">
        A rolling assessment across every core Network Engineer competency, updated after every resolved incident.
      </p>

      {report && (
        <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="rounded-lg border border-accent-500/30 bg-accent-500/5 p-6 text-center lg:col-span-1">
            <p className="text-xs uppercase tracking-wide text-accent-400">Network Engineer Readiness</p>
            <p className="mt-3 text-5xl font-bold text-slate-100">{report.overall_readiness}%</p>
            <p className="mt-2 text-lg font-medium text-accent-400">{report.level}</p>
            {report.improvement_areas.length > 0 && (
              <div className="mt-6 text-left">
                <p className="text-xs uppercase tracking-wide text-slate-500">Focus areas</p>
                <ul className="mt-2 space-y-1">
                  {report.improvement_areas.map((a) => (
                    <li key={a} className="text-sm text-slate-300">
                      • {a}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          <div className="rounded-lg border border-ink-700 bg-ink-900 p-6 lg:col-span-2">
            <p className="mb-4 text-xs uppercase tracking-wide text-slate-500">Skill breakdown</p>
            <div className="space-y-4">
              {SKILL_LABELS.map(([key, label]) => {
                const value = report[key] as number;
                return (
                  <div key={key}>
                    <div className="mb-1 flex items-center justify-between text-sm">
                      <span className="text-slate-300">{label}</span>
                      <span className="font-mono text-slate-400">{value}%</span>
                    </div>
                    <div className="h-2 w-full overflow-hidden rounded-full bg-ink-800">
                      <div className={`h-full ${barColor(value)}`} style={{ width: `${Math.min(100, value)}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </AuthGuard>
  );
}

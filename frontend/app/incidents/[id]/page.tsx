"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useSearchParams, useRouter } from "next/navigation";
import AuthGuard from "@/components/AuthGuard";
import TopologyDiagram from "@/components/TopologyDiagram";
import CliTerminal from "@/components/CliTerminal";
import CoachPanel from "@/components/CoachPanel";
import { api, ApiError } from "@/lib/api";
import { AttemptPublic, CoachTurn, IncidentPublic, ResolutionSummary } from "@/lib/types";

const METHODOLOGY_STEPS: [string, string][] = [
  ["identify_problem", "Identify the problem"],
  ["check_layer1", "Check Layer 1"],
  ["check_layer2", "Check Layer 2"],
  ["check_layer3", "Check Layer 3"],
  ["form_hypothesis", "Form a hypothesis"],
  ["implement_fix", "Implement the fix"],
  ["verify_fix", "Verify the fix"],
];

function ScoreRow({ label, value }: { label: string; value: number }) {
  const color = value >= 80 ? "text-signal-green" : value >= 50 ? "text-signal-amber" : "text-signal-red";
  return (
    <div className="flex items-center justify-between border-b border-ink-800 py-2 text-sm">
      <span className="text-slate-400">{label}</span>
      <span className={`font-mono font-semibold ${color}`}>{value}%</span>
    </div>
  );
}

export default function IncidentWorkspacePage() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const router = useRouter();
  const incidentId = params.id;
  const [attemptId, setAttemptId] = useState<string | null>(searchParams.get("attempt"));

  const [incident, setIncident] = useState<IncidentPublic | null>(null);
  const [attempt, setAttempt] = useState<AttemptPublic | null>(null);
  const [transcript, setTranscript] = useState<CoachTurn[]>([]);
  const [selectedDevice, setSelectedDevice] = useState<string | null>(null);
  const [diagnosis, setDiagnosis] = useState("");
  const [diagnosisResult, setDiagnosisResult] = useState<string | null>(null);
  const [resolution, setResolution] = useState<ResolutionSummary | null>(null);
  const [verifyError, setVerifyError] = useState<string | null>(null);
  const [verifying, setVerifying] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  const loadAttempt = useCallback(async (id: string) => {
    const [a, t] = await Promise.all([
      api.get<AttemptPublic>(`/incidents/attempts/${id}`),
      api.get<{ transcript: CoachTurn[] }>(`/incidents/attempts/${id}/transcript`),
    ]);
    setAttempt(a);
    setTranscript(t.transcript);
  }, []);

  useEffect(() => {
    api
      .get<IncidentPublic>(`/incidents/${incidentId}`)
      .then((inc) => {
        setIncident(inc);
        setSelectedDevice(inc.topology.nodes[0]?.id || null);
      })
      .catch((e) => setLoadError(e.message));
  }, [incidentId]);

  useEffect(() => {
    if (!attemptId) return;
    loadAttempt(attemptId).catch((e) => setLoadError(e.message));
  }, [attemptId, loadAttempt]);

  async function ensureAttempt(): Promise<string> {
    if (attemptId) return attemptId;
    const a = await api.post<AttemptPublic>("/incidents/attempts", { incident_id: incidentId });
    setAttemptId(a.id);
    router.replace(`/incidents/${incidentId}?attempt=${a.id}`);
    return a.id;
  }

  async function runCommand(device: string, command: string): Promise<string> {
    const id = await ensureAttempt();
    const res = await api.post<{ output: string }>(`/incidents/attempts/${id}/cli`, { device, command });
    loadAttempt(id).catch(() => {});
    return res.output;
  }

  async function sendCoachMessage(message: string) {
    if (!attemptId) return;
    const res = await api.post<{ transcript: CoachTurn[] }>(`/incidents/attempts/${attemptId}/coach`, { message });
    setTranscript(res.transcript);
  }

  async function requestHint() {
    if (!attemptId) return;
    await api.post(`/incidents/attempts/${attemptId}/hint`);
    loadAttempt(attemptId).catch(() => {});
  }

  async function submitDiagnosis() {
    if (!attemptId || !diagnosis.trim()) return;
    const res = await api.post<{ matched: boolean }>(`/incidents/attempts/${attemptId}/diagnose`, {
      root_cause_statement: diagnosis,
    });
    setDiagnosisResult(
      res.matched
        ? "That matches the evidence. Now apply the fix and verify it."
        : "Not quite — re-check the evidence you've gathered and try again, or request a hint."
    );
    loadAttempt(attemptId).catch(() => {});
  }

  async function verifyFix() {
    if (!attemptId || !incident) return;
    setVerifying(true);
    setVerifyError(null);
    try {
      const pcNode = incident.topology.nodes.find((n) => n.type === "pc") || incident.topology.nodes[0];
      const res = await api.post<ResolutionSummary>(`/incidents/attempts/${attemptId}/verify`, {
        device: pcNode.id,
        command: "ping",
      });
      setResolution(res);
      setAttempt(res.attempt);
    } catch (e) {
      setVerifyError(e instanceof ApiError ? e.message : "Verification failed.");
    } finally {
      setVerifying(false);
    }
  }

  if (loadError) {
    return (
      <AuthGuard>
        <p className="text-sm text-signal-red">{loadError}</p>
      </AuthGuard>
    );
  }

  if (!incident) {
    return (
      <AuthGuard>
        <p className="text-sm text-slate-500">Loading incident…</p>
      </AuthGuard>
    );
  }

  return (
    <AuthGuard>
      <div className="mb-4 flex items-center justify-between">
        <div>
          <p className="font-mono text-xs uppercase tracking-wide text-accent-400">
            {incident.priority} · {incident.category}
          </p>
          <h1 className="text-xl font-semibold text-slate-100">{incident.title}</h1>
        </div>
        {attempt?.status === "resolved" && (
          <span className="rounded-full border border-signal-green/40 bg-signal-green/10 px-3 py-1 text-xs font-medium text-signal-green">
            Resolved · {attempt.score_overall}%
          </span>
        )}
      </div>

      {resolution ? (
        <div className="rounded-lg border border-signal-green/30 bg-ink-900 p-6">
          <h2 className="text-lg font-semibold text-signal-green">Incident Resolved</h2>
          <p className="mt-2 text-sm text-slate-300">{resolution.explanation}</p>

          <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
            <div>
              <p className="mb-2 text-xs uppercase tracking-wide text-slate-500">Network Engineer Score</p>
              <ScoreRow label="Diagnosis" value={resolution.attempt.score_diagnosis ?? 0} />
              <ScoreRow label="Methodology" value={resolution.attempt.score_methodology ?? 0} />
              <ScoreRow label="Efficiency" value={resolution.attempt.score_efficiency ?? 0} />
              <ScoreRow label="Remediation" value={resolution.attempt.score_remediation ?? 0} />
              <ScoreRow label="Verification" value={resolution.attempt.score_verification ?? 0} />
            </div>
            <div className="rounded-lg border border-ink-700 bg-ink-850 p-4">
              <p className="text-xs uppercase tracking-wide text-slate-500">Overall</p>
              <p className="mt-1 text-4xl font-bold text-signal-green">{resolution.attempt.score_overall}%</p>
              <p className="mt-2 text-xs text-slate-500">
                {resolution.attempt.hints_used} hints · {resolution.attempt.failed_attempts} failed attempts ·{" "}
                {resolution.attempt.unnecessary_commands} unnecessary commands
              </p>
              <div className="mt-4 space-y-2 text-xs text-slate-400">
                <p>
                  <span className="text-slate-500">Root cause:</span> {resolution.root_cause}
                </p>
                <p>
                  <span className="text-slate-500">Fix:</span> {resolution.correct_remediation}
                </p>
              </div>
            </div>
          </div>

          <div className="mt-6 flex gap-3">
            <button
              onClick={() => router.push("/incidents")}
              className="rounded-md bg-accent-500 px-4 py-2 text-sm font-semibold text-ink-950 hover:bg-accent-400"
            >
              Back to Incidents
            </button>
            <button
              onClick={() => router.push("/dashboard")}
              className="rounded-md border border-ink-600 px-4 py-2 text-sm text-slate-300 hover:bg-ink-800"
            >
              View Dashboard
            </button>
          </div>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-[280px_1fr_320px]">
            {/* LEFT: incident details */}
            <div className="rounded-lg border border-ink-700 bg-ink-900 p-4">
              <p className="text-xs uppercase tracking-wide text-slate-500">Impact</p>
              <p className="mt-1 text-sm text-slate-300">{incident.impact}</p>

              <p className="mt-4 text-xs uppercase tracking-wide text-slate-500">Symptoms</p>
              <ul className="mt-1 space-y-1">
                {incident.symptoms.map((s, i) => (
                  <li key={i} className="text-sm text-slate-300">
                    • {s}
                  </li>
                ))}
              </ul>

              <p className="mt-4 text-xs uppercase tracking-wide text-slate-500">Methodology</p>
              <ul className="mt-2 space-y-1.5">
                {METHODOLOGY_STEPS.map(([key, label]) => {
                  const done = attempt?.methodology_progress?.[key];
                  return (
                    <li key={key} className="flex items-center gap-2 text-xs">
                      <span className={`h-1.5 w-1.5 rounded-full ${done ? "bg-signal-green" : "bg-ink-700"}`} />
                      <span className={done ? "text-slate-300" : "text-slate-600"}>{label}</span>
                    </li>
                  );
                })}
              </ul>
            </div>

            {/* CENTER: topology */}
            <div className="flex flex-col gap-4">
              <TopologyDiagram
                nodes={incident.topology.nodes}
                edges={incident.topology.edges}
                selectedDevice={selectedDevice}
                onSelectDevice={setSelectedDevice}
              />

              <div className="rounded-lg border border-ink-700 bg-ink-900 p-4">
                <p className="mb-2 text-xs uppercase tracking-wide text-slate-500">Submit Root Cause</p>
                <textarea
                  value={diagnosis}
                  onChange={(e) => setDiagnosis(e.target.value)}
                  placeholder="Describe what you believe the root cause is, in your own words…"
                  rows={2}
                  className="w-full rounded-md border border-ink-600 bg-ink-850 px-3 py-2 text-sm text-slate-100 outline-none focus:border-accent-500"
                />
                <div className="mt-2 flex items-center gap-3">
                  <button
                    onClick={submitDiagnosis}
                    className="rounded-md border border-accent-500/50 bg-accent-500/10 px-3 py-1.5 text-xs font-medium text-accent-400 hover:bg-accent-500/20"
                  >
                    Submit Diagnosis
                  </button>
                  <button
                    onClick={verifyFix}
                    disabled={verifying}
                    className="rounded-md bg-signal-green/90 px-3 py-1.5 text-xs font-semibold text-ink-950 hover:bg-signal-green disabled:opacity-60"
                  >
                    {verifying ? "Verifying…" : "Verify Fix"}
                  </button>
                </div>
                {diagnosisResult && <p className="mt-2 text-xs text-slate-400">{diagnosisResult}</p>}
                {verifyError && <p className="mt-2 text-xs text-signal-red">{verifyError}</p>}
              </div>
            </div>

            {/* RIGHT: AI coach */}
            <CoachPanel transcript={transcript} hintsUsed={attempt?.hints_used || 0} onSendMessage={sendCoachMessage} onRequestHint={requestHint} />
          </div>

          {/* BOTTOM: CLI terminal */}
          <div className="mt-4">
            <CliTerminal
              devices={incident.topology.nodes}
              selectedDevice={selectedDevice}
              onSelectDevice={setSelectedDevice}
              onRunCommand={runCommand}
            />
          </div>
        </>
      )}
    </AuthGuard>
  );
}

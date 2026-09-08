"use client";

import { useState } from "react";
import AuthGuard from "@/components/AuthGuard";
import { PACKET_SCENARIOS, PacketStage } from "@/data/packetScenarios";

const LAYER_COLOR: Record<string, string> = {
  Application: "bg-signal-blue/15 text-signal-blue border-signal-blue/40",
  "Transport (TCP/UDP)": "bg-accent-500/15 text-accent-400 border-accent-500/40",
  "Network (IP)": "bg-signal-amber/15 text-signal-amber border-signal-amber/40",
  "Data Link (Ethernet)": "bg-signal-green/15 text-signal-green border-signal-green/40",
  Physical: "bg-slate-500/15 text-slate-400 border-slate-500/40",
};

export default function PacketVisualiserPage() {
  const [scenarioId, setScenarioId] = useState(PACKET_SCENARIOS[0].id);
  const scenario = PACKET_SCENARIOS.find((s) => s.id === scenarioId)!;
  const [activeIndex, setActiveIndex] = useState(0);
  const activeStage: PacketStage = scenario.stages[activeIndex];

  function selectScenario(id: string) {
    setScenarioId(id);
    setActiveIndex(0);
  }

  return (
    <AuthGuard>
      <h1 className="text-2xl font-semibold text-slate-100">Follow the Packet</h1>
      <p className="mt-1 text-sm text-slate-500">
        Pick an action and step through exactly what happens on the network — layer by layer, hop by hop.
      </p>

      <div className="mt-6 flex flex-wrap gap-2">
        {PACKET_SCENARIOS.map((s) => (
          <button
            key={s.id}
            onClick={() => selectScenario(s.id)}
            className={`rounded-md border px-4 py-2 text-sm font-medium transition-colors ${
              s.id === scenarioId
                ? "border-accent-500 bg-accent-500/10 text-accent-400"
                : "border-ink-700 bg-ink-900 text-slate-400 hover:border-ink-600"
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>
      <p className="mt-2 text-sm text-slate-500">{scenario.description}</p>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-[1fr_380px]">
        {/* Stage flow */}
        <div className="rounded-lg border border-ink-700 bg-ink-900 p-5">
          <div className="scrollbar-thin flex gap-2 overflow-x-auto pb-2">
            {scenario.stages.map((stage, i) => (
              <button
                key={stage.id}
                onClick={() => setActiveIndex(i)}
                className={`flex min-w-[140px] flex-col items-start rounded-md border px-3 py-2 text-left transition-colors ${
                  i === activeIndex ? "border-accent-500 bg-accent-500/10" : "border-ink-700 bg-ink-850 hover:border-ink-600"
                }`}
              >
                <span className="font-mono text-[10px] text-slate-500">Step {i + 1}</span>
                <span className={`mt-1 text-xs font-medium ${i === activeIndex ? "text-accent-400" : "text-slate-300"}`}>
                  {stage.title}
                </span>
              </button>
            ))}
          </div>

          <div className="mt-6 flex items-center gap-3">
            {scenario.stages.map((_, i) => (
              <div key={i} className="flex items-center">
                <div
                  className={`h-2.5 w-2.5 rounded-full ${i <= activeIndex ? "bg-accent-500" : "bg-ink-700"}`}
                  title={`Step ${i + 1}`}
                />
                {i < scenario.stages.length - 1 && (
                  <div className={`h-0.5 w-8 ${i < activeIndex ? "bg-accent-500" : "bg-ink-700"}`} />
                )}
              </div>
            ))}
          </div>

          <div className="mt-6">
            <div className="mb-2 flex items-center gap-2">
              <span className={`rounded-full border px-2 py-0.5 text-[10px] font-medium ${LAYER_COLOR[activeStage.layer]}`}>
                {activeStage.layer}
              </span>
              <span className="text-xs text-slate-500">{activeStage.location}</span>
            </div>
            <h2 className="text-lg font-semibold text-slate-100">{activeStage.title}</h2>
            <p className="mt-2 text-sm leading-relaxed text-slate-400">{activeStage.description}</p>
          </div>

          <div className="mt-6 flex justify-between">
            <button
              onClick={() => setActiveIndex((i) => Math.max(0, i - 1))}
              disabled={activeIndex === 0}
              className="rounded-md border border-ink-600 px-4 py-2 text-sm text-slate-300 hover:bg-ink-800 disabled:opacity-40"
            >
              ← Previous
            </button>
            <button
              onClick={() => setActiveIndex((i) => Math.min(scenario.stages.length - 1, i + 1))}
              disabled={activeIndex === scenario.stages.length - 1}
              className="rounded-md bg-accent-500 px-4 py-2 text-sm font-semibold text-ink-950 hover:bg-accent-400 disabled:opacity-40"
            >
              Next →
            </button>
          </div>
        </div>

        {/* Header inspector */}
        <div className="rounded-lg border border-ink-700 bg-ink-900 p-5">
          <p className="text-xs uppercase tracking-wide text-slate-500">Header Inspector</p>
          {activeStage.headers ? (
            <div className="mt-3 space-y-2 font-mono text-xs">
              {activeStage.headers.map(([k, v]) => (
                <div key={k} className="flex justify-between gap-3 border-b border-ink-800 py-1.5">
                  <span className="text-slate-500">{k}</span>
                  <span className="text-right text-accent-400">{v}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="mt-3 text-sm text-slate-600">No packet header at this step — this is an application- or process-level event.</p>
          )}

          <div className="mt-6 rounded-md border border-ink-700 bg-ink-850 p-3">
            <p className="text-xs uppercase tracking-wide text-slate-500">Encapsulation</p>
            <div className="mt-2 space-y-1 text-xs text-slate-400">
              <p>Application Data</p>
              <p className="pl-3">↓ TCP/UDP Segment</p>
              <p className="pl-6">↓ IP Packet</p>
              <p className="pl-9">↓ Ethernet Frame</p>
              <p className="pl-12">↓ Physical Transmission</p>
            </div>
          </div>
        </div>
      </div>
    </AuthGuard>
  );
}

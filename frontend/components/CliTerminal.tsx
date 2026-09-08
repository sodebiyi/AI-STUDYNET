"use client";

import { useState, useRef, useEffect, KeyboardEvent } from "react";
import { TopologyNode } from "@/lib/types";

interface HistoryEntry {
  device: string;
  command: string;
  output: string;
}

interface Props {
  devices: TopologyNode[];
  selectedDevice: string | null;
  onSelectDevice: (id: string) => void;
  onRunCommand: (device: string, command: string) => Promise<string>;
}

const COMMON_COMMANDS = [
  "show ip interface brief",
  "show running-config",
  "show vlan brief",
  "show interfaces trunk",
  "show mac address-table",
  "show ip route",
  "show ip ospf neighbor",
  "show arp",
  "show cdp neighbors",
  "ping ",
  "traceroute ",
  "configure terminal",
];

export default function CliTerminal({ devices, selectedDevice, onSelectDevice, onRunCommand }: Props) {
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [input, setInput] = useState("");
  const [running, setRunning] = useState(false);
  const [cmdHistoryIdx, setCmdHistoryIdx] = useState<number | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [history]);

  async function submit() {
    const device = selectedDevice || devices[0]?.id;
    if (!device || !input.trim() || running) return;
    const command = input;
    setInput("");
    setRunning(true);
    try {
      const output = await onRunCommand(device, command);
      setHistory((h) => [...h, { device, command, output }]);
    } catch (e) {
      setHistory((h) => [...h, { device, command, output: `% Error: ${e instanceof Error ? e.message : "request failed"}` }]);
    } finally {
      setRunning(false);
      setCmdHistoryIdx(null);
    }
  }

  function onKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") {
      submit();
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      const cmds = history.map((h) => h.command);
      if (cmds.length === 0) return;
      const nextIdx = cmdHistoryIdx === null ? cmds.length - 1 : Math.max(0, cmdHistoryIdx - 1);
      setCmdHistoryIdx(nextIdx);
      setInput(cmds[nextIdx]);
    }
  }

  return (
    <div className="flex h-full flex-col rounded-lg border border-ink-700 bg-black font-mono text-xs">
      <div className="flex items-center gap-2 border-b border-ink-700 bg-ink-900 px-3 py-2">
        <span className="text-slate-400">Device:</span>
        <select
          value={selectedDevice || ""}
          onChange={(e) => onSelectDevice(e.target.value)}
          className="rounded border border-ink-600 bg-ink-850 px-2 py-1 text-slate-200"
        >
          {devices.map((d) => (
            <option key={d.id} value={d.id}>
              {d.label}
            </option>
          ))}
        </select>
        <div className="ml-auto flex flex-wrap justify-end gap-1">
          {COMMON_COMMANDS.slice(0, 5).map((c) => (
            <button
              key={c}
              onClick={() => setInput(c)}
              className="rounded border border-ink-700 px-1.5 py-0.5 text-[10px] text-slate-400 hover:border-accent-500 hover:text-accent-400"
            >
              {c.trim()}
            </button>
          ))}
        </div>
      </div>

      <div ref={scrollRef} className="scrollbar-thin flex-1 overflow-y-auto px-3 py-2 text-slate-300" style={{ minHeight: 220, maxHeight: 320 }}>
        {history.length === 0 && (
          <p className="text-slate-600">
            Type a command below (e.g. <span className="text-accent-400">show ip interface brief</span>) to start investigating.
          </p>
        )}
        {history.map((h, i) => (
          <div key={i} className="mb-3">
            <div className="text-accent-400">
              {h.device}#{" "}
              <span className="text-slate-200">{h.command}</span>
            </div>
            <pre className="whitespace-pre-wrap text-slate-400">{h.output}</pre>
          </div>
        ))}
      </div>

      <div className="flex items-center gap-2 border-t border-ink-700 px-3 py-2">
        <span className="text-accent-400">{(selectedDevice || devices[0]?.id || "device")}#</span>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          disabled={running}
          placeholder="show ip interface brief"
          className="flex-1 bg-transparent text-slate-100 outline-none placeholder:text-slate-700"
          autoComplete="off"
          spellCheck={false}
        />
        {running && <span className="pulse-dot text-slate-500">running…</span>}
      </div>
    </div>
  );
}

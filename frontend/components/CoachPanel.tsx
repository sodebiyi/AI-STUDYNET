"use client";

import { useState, useRef, useEffect, FormEvent } from "react";
import { CoachTurn } from "@/lib/types";

interface Props {
  transcript: CoachTurn[];
  hintsUsed: number;
  onSendMessage: (message: string) => Promise<void>;
  onRequestHint: () => Promise<void>;
}

export default function CoachPanel({ transcript, hintsUsed, onSendMessage, onRequestHint }: Props) {
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [hintLoading, setHintLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [transcript]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!input.trim() || sending) return;
    const message = input;
    setInput("");
    setSending(true);
    try {
      await onSendMessage(message);
    } finally {
      setSending(false);
    }
  }

  async function requestHint() {
    setHintLoading(true);
    try {
      await onRequestHint();
    } finally {
      setHintLoading(false);
    }
  }

  return (
    <div className="flex h-full flex-col rounded-lg border border-ink-700 bg-ink-900">
      <div className="flex items-center justify-between border-b border-ink-700 px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-signal-green" />
          <span className="text-sm font-semibold text-slate-100">NetMentor Coach</span>
        </div>
        <span className="text-xs text-slate-500">Hints used: {hintsUsed}</span>
      </div>

      <div ref={scrollRef} className="scrollbar-thin flex-1 space-y-3 overflow-y-auto px-4 py-3" style={{ minHeight: 260, maxHeight: 420 }}>
        {transcript.map((turn, i) => (
          <div key={i} className={`flex ${turn.role === "student" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[85%] rounded-lg px-3 py-2 text-sm leading-relaxed ${
                turn.role === "student" ? "bg-accent-500/15 text-accent-100" : "bg-ink-800 text-slate-300"
              }`}
            >
              {turn.text}
            </div>
          </div>
        ))}
      </div>

      <div className="border-t border-ink-700 p-3">
        <button
          onClick={requestHint}
          disabled={hintLoading}
          className="mb-2 w-full rounded-md border border-signal-amber/40 bg-signal-amber/10 px-3 py-1.5 text-xs font-medium text-signal-amber hover:bg-signal-amber/20 disabled:opacity-60"
        >
          {hintLoading ? "Getting hint…" : "Request Hint"}
        </button>
        <form onSubmit={onSubmit} className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Tell the coach what you've found…"
            disabled={sending}
            className="flex-1 rounded-md border border-ink-600 bg-ink-850 px-3 py-2 text-sm text-slate-100 outline-none focus:border-accent-500"
          />
          <button
            type="submit"
            disabled={sending}
            className="rounded-md bg-accent-500 px-4 py-2 text-sm font-semibold text-ink-950 hover:bg-accent-400 disabled:opacity-60"
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
}

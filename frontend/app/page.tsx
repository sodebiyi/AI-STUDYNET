"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";

export default function LandingPage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && user) router.replace("/dashboard");
  }, [loading, user, router]);

  return (
    <div className="flex min-h-screen flex-col bg-ink-950">
      <header className="mx-auto flex w-full max-w-6xl items-center justify-between px-6 py-6">
        <div className="flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded bg-accent-500/15 text-accent-400 font-mono text-xs font-bold">
            NM
          </span>
          <span className="font-semibold tracking-tight">NetMentor AI</span>
        </div>
        <div className="flex gap-3">
          <Link href="/login" className="rounded-md px-4 py-2 text-sm text-slate-300 hover:text-white">
            Sign in
          </Link>
          <Link href="/register" className="rounded-md bg-accent-500 px-4 py-2 text-sm font-medium text-ink-950 hover:bg-accent-400">
            Get started
          </Link>
        </div>
      </header>

      <section className="mx-auto flex w-full max-w-4xl flex-1 flex-col items-center justify-center px-6 py-24 text-center">
        <p className="mb-4 font-mono text-xs uppercase tracking-[0.3em] text-accent-400">NetMentor AI</p>
        <h1 className="text-4xl font-bold tracking-tight text-slate-50 sm:text-5xl">
          Don&rsquo;t just learn networking.
          <br />
          Learn how to troubleshoot like a Network Engineer.
        </h1>
        <p className="mt-6 max-w-2xl text-lg text-slate-400">
          Realistic NOC-style incidents, a simulated Cisco CLI, and an AI coach that asks questions instead of
          handing you answers — built for CCNA/CCNP students, NOC engineers, and anyone prepping for a Network
          Engineer interview.
        </p>
        <div className="mt-10 flex gap-4">
          <Link
            href="/register"
            className="rounded-md bg-accent-500 px-6 py-3 text-sm font-semibold text-ink-950 hover:bg-accent-400"
          >
            Start troubleshooting — free
          </Link>
          <Link
            href="/login"
            className="rounded-md border border-ink-600 px-6 py-3 text-sm font-semibold text-slate-200 hover:bg-ink-800"
          >
            Sign in
          </Link>
        </div>

        <div className="mt-20 grid w-full grid-cols-1 gap-4 text-left sm:grid-cols-3">
          {[
            { title: "Follow the Packet", body: "Watch a request travel from browser to server, header by realistic header." },
            { title: "Network Incidents", body: "Investigate NOC-style tickets with a live simulated CLI — no answers handed to you." },
            { title: "AI Network Coach", body: "Socratic questioning that builds real troubleshooting instinct, not copy-paste fixes." },
          ].map((f) => (
            <div key={f.title} className="rounded-lg border border-ink-700 bg-ink-900 p-5">
              <h3 className="text-sm font-semibold text-accent-400">{f.title}</h3>
              <p className="mt-2 text-sm text-slate-400">{f.body}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

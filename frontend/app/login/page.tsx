"use client";

import { useState, FormEvent } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { ApiError } from "@/lib/api";

export default function LoginPage() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-ink-950 px-6">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <span className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded bg-accent-500/15 text-accent-400 font-mono text-sm font-bold">
            NM
          </span>
          <h1 className="text-xl font-semibold text-slate-100">Sign in to NetMentor AI</h1>
        </div>

        <form onSubmit={onSubmit} className="space-y-4 rounded-lg border border-ink-700 bg-ink-900 p-6">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-400">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-md border border-ink-600 bg-ink-850 px-3 py-2 text-sm text-slate-100 outline-none focus:border-accent-500"
              placeholder="you@example.com"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-400">Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-md border border-ink-600 bg-ink-850 px-3 py-2 text-sm text-slate-100 outline-none focus:border-accent-500"
              placeholder="••••••••"
            />
          </div>
          {error && <p className="text-xs text-signal-red">{error}</p>}
          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-md bg-accent-500 px-4 py-2 text-sm font-semibold text-ink-950 hover:bg-accent-400 disabled:opacity-60"
          >
            {submitting ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <p className="mt-4 text-center text-sm text-slate-500">
          No account?{" "}
          <Link href="/register" className="text-accent-400 hover:underline">
            Create one
          </Link>
        </p>
      </div>
    </div>
  );
}

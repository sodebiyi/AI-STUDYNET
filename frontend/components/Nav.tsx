"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

const LINKS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/packet-visualiser", label: "Follow the Packet" },
  { href: "/incidents", label: "Incidents" },
  { href: "/readiness", label: "Am I Job Ready?" },
];

export default function Nav() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <header className="sticky top-0 z-40 border-b border-ink-700 bg-ink-950/95 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-3">
        <div className="flex items-center gap-8">
          <Link href="/dashboard" className="flex items-center gap-2">
            <span className="flex h-7 w-7 items-center justify-center rounded bg-accent-500/15 text-accent-400 font-mono text-xs font-bold">
              NM
            </span>
            <span className="text-sm font-semibold tracking-tight text-slate-100">NetMentor AI</span>
          </Link>
          <nav className="hidden gap-1 md:flex">
            {LINKS.map((link) => {
              const active = pathname?.startsWith(link.href);
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`rounded-md px-3 py-1.5 text-sm transition-colors ${
                    active ? "bg-ink-800 text-accent-400" : "text-slate-400 hover:bg-ink-800 hover:text-slate-200"
                  }`}
                >
                  {link.label}
                </Link>
              );
            })}
          </nav>
        </div>
        {user && (
          <div className="flex items-center gap-3 text-sm">
            <span className="hidden text-slate-400 sm:inline">
              {user.display_name} · <span className="text-accent-400">{user.xp} XP</span>
            </span>
            <button
              onClick={logout}
              className="rounded-md border border-ink-600 px-3 py-1.5 text-xs font-medium text-slate-300 hover:bg-ink-800"
            >
              Sign out
            </button>
          </div>
        )}
      </div>
    </header>
  );
}

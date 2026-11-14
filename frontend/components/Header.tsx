"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect } from "react";
import { USE_MOCKS } from "../lib/config";
import { useUserId } from "../lib/hooks";
import { resetMock } from "../lib/mock";
import { loadStoredUser, setUserId } from "../lib/session";
import { PEOPLE, type UserId } from "../lib/types";

const NAV = [
  { href: "/expert", label: "Expert" },
  { href: "/successor", label: "Successor" },
  { href: "/compare", label: "Memory on vs off" },
  { href: "/audit", label: "Audit" },
];

export function Header() {
  const user = useUserId();
  const path = usePathname();
  useEffect(() => loadStoredUser(), []);

  return (
    <header className="sticky top-0 z-20 border-b border-line bg-bg/90 backdrop-blur">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-3 px-4 py-3 sm:px-6">
        <Link href="/" className="font-serif text-xl tracking-tight">
          Handover
        </Link>
        <nav className="flex flex-wrap gap-1 text-sm">
          {NAV.map((n) => (
            <Link
              key={n.href}
              href={n.href}
              className={`rounded-md px-3 py-1.5 transition-colors ${
                path === n.href ? "bg-ink text-white" : "text-muted hover:bg-line/60 hover:text-ink"
              }`}
            >
              {n.label}
            </Link>
          ))}
        </nav>
        <div className="ml-auto flex items-center gap-3">
          {USE_MOCKS && (
            <span className="flex items-center gap-2">
              <span
                className="rounded-full border border-warn/30 bg-warn-soft px-2.5 py-1 text-xs font-medium text-warn"
                title="Fictional in-browser data. Not connected to the backend."
              >
                Mock data
              </span>
              <button onClick={() => resetMock()} className="text-xs text-muted underline-offset-2 hover:underline">
                Reset
              </button>
            </span>
          )}
          <label className="flex items-center gap-2 text-sm">
            <span className="text-muted">Viewing as</span>
            <select
              value={user}
              onChange={(e) => setUserId(e.target.value as UserId)}
              className="rounded-md border border-line bg-surface px-2 py-1.5 text-sm focus:outline-2 focus:outline-accent"
            >
              {PEOPLE.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.role})
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>
    </header>
  );
}

"use client";

import { api } from "../lib/api";
import type { Memory } from "../lib/types";

export function Card({ title, aside, children, className = "" }: { title?: React.ReactNode; aside?: React.ReactNode; children: React.ReactNode; className?: string }) {
  return (
    <section className={`rounded-xl border border-line bg-surface p-5 ${className}`}>
      {(title || aside) && (
        <div className="mb-4 flex items-center justify-between gap-3">
          {title && <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">{title}</h2>}
          {aside}
        </div>
      )}
      {children}
    </section>
  );
}

export function PageTitle({ title, sub }: { title: string; sub: string }) {
  return (
    <div className="mb-8 max-w-2xl">
      <h1 className="font-serif text-3xl tracking-tight">{title}</h1>
      <p className="mt-2 text-muted">{sub}</p>
    </div>
  );
}

export function ErrorNote({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="rounded-lg border border-danger/25 bg-danger-soft px-4 py-3 text-sm text-danger">
      {message}
      {onRetry && (
        <button onClick={onRetry} className="ml-3 font-medium underline underline-offset-2">
          Retry
        </button>
      )}
    </div>
  );
}

export function Loading({ label = "Loading" }: { label?: string }) {
  return <p className="animate-pulse text-sm text-muted">{label}…</p>;
}

export function Button({ variant = "primary", className = "", ...props }: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "ghost" | "danger" }) {
  const styles = {
    primary: "bg-accent text-white hover:bg-accent/90",
    ghost: "border border-line bg-surface text-ink hover:bg-bg",
    danger: "bg-danger text-white hover:bg-danger/90",
  }[variant];
  return (
    <button
      {...props}
      className={`rounded-lg px-3.5 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${styles} ${className}`}
    />
  );
}

const SCOPE_STYLE: Record<string, string> = {
  successor: "bg-accent-soft text-accent",
  team: "bg-line/70 text-ink",
  never_transfer: "bg-danger-soft text-danger",
};

export function Tag({ children, tone = "neutral" }: { children: React.ReactNode; tone?: string }) {
  const cls = SCOPE_STYLE[tone] ?? "bg-bg text-muted border border-line";
  return <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}>{children}</span>;
}

export function MemoryMeta({ m }: { m: Memory }) {
  return (
    <div className="flex flex-wrap items-center gap-1.5 text-xs text-muted">
      <Tag>{m.kind}</Tag>
      <Tag tone={m.scope}>{m.scope.replace("_", " ")}</Tag>
      <span>v{m.version}</span>
      <span className="font-mono">{m.id}</span>
      <span>expires {new Date(m.expires_at).toLocaleDateString()}</span>
    </div>
  );
}

export function Audio({ url, label }: { url: string | null; label?: string }) {
  const src = api.mediaUrl(url);
  if (!src) return <p className="text-xs text-muted">No recording attached{label ? ` (${label})` : ""}.</p>;
  return <audio controls preload="none" src={src} className="h-9 w-full max-w-md" />;
}

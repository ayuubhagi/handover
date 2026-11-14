"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "../lib/api";
import type { Memory, MemoryScope } from "../lib/types";
import { IconKey, IconLock, IconPause, IconPlay, IconUsers } from "./icons";

export function Card({ title, aside, children, className = "" }: { title?: React.ReactNode; aside?: React.ReactNode; children: React.ReactNode; className?: string }) {
  return (
    <section className={`rounded-2xl border border-line bg-surface p-5 ${className}`}>
      {(title || aside) && (
        <div className="mb-4 flex items-center justify-between gap-3">
          {title && <h2 className="text-sm font-semibold text-ink">{title}</h2>}
          {aside}
        </div>
      )}
      {children}
    </section>
  );
}

export function ErrorNote({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="rounded-xl border border-danger/25 bg-danger-soft px-4 py-3 text-sm text-danger">
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

export function Button({ variant = "primary", className = "", ...props }: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "ghost" | "danger" | "accent" }) {
  const styles = {
    primary: "bg-primary text-on-primary hover:opacity-90",
    accent: "bg-accent text-on-accent hover:opacity-90",
    ghost: "border border-line bg-surface text-ink hover:bg-hover",
    danger: "bg-danger text-white hover:opacity-90",
  }[variant];
  return (
    <button
      {...props}
      className={`inline-flex items-center justify-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50 ${styles} ${className}`}
    />
  );
}

const SCOPE_STYLE: Record<string, string> = {
  successor: "bg-accent-soft text-accent-ink",
  team: "bg-hover text-ink",
  never_transfer: "bg-danger-soft text-danger",
};

export function Tag({ children, tone = "neutral" }: { children: React.ReactNode; tone?: string }) {
  const cls = SCOPE_STYLE[tone] ?? "bg-bg text-muted border border-line";
  return <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}>{children}</span>;
}

/** Technical metadata row (Under the hood only). */
export function MemoryMeta({ m }: { m: Memory }) {
  return (
    <div className="flex flex-wrap items-center gap-1.5 text-xs text-muted">
      <Tag>{m.kind}</Tag>
      <span title={audienceTip(m.scope)}>
        <Tag tone={m.scope}>
          <ScopeIcon scope={m.scope} />
          {audienceLabel(m.scope)}
        </Tag>
      </span>
      <span>v{m.version}</span>
      <span className="font-mono">{m.id}</span>
      <span>expires {new Date(m.expires_at).toLocaleDateString()}</span>
    </div>
  );
}

/** Plain-language access levels. Banks run on need-to-know and segregation of duties. */
export const AUDIENCE: { value: MemoryScope; label: string; tip: string }[] = [
  {
    value: "never_transfer",
    label: "Senior only",
    tip: "Client-confidential. Privacy and bank confidentiality rules say nobody else gets it, not even the successor.",
  },
  {
    value: "successor",
    label: "Successor",
    tip: "Authority and override knowledge, like moving money around a control. Only the person accountable for the role gets it.",
  },
  {
    value: "team",
    label: "Everyone on the team",
    tip: "General know-how. Safe, and it helps the intern learn.",
  },
];
export const audienceTip = (s: MemoryScope) => AUDIENCE.find((a) => a.value === s)?.tip;

/** Plain-language line for answers where some matches were withheld by role. */
export function withheldText(n: number): string {
  return `${n} ${n === 1 ? "memory is" : "memories are"} restricted for your role, so ${n === 1 ? "it was" : "they were"} withheld. This was logged.`;
}
export const audienceLabel = (s: MemoryScope) => AUDIENCE.find((a) => a.value === s)?.label ?? s;

/** Plays an API audio URL; falls back to reading the text aloud when there is no recording. */
export function PlayButton({ url, text, label, autoPlay = false }: { url: string | null; text?: string; label: string; autoPlay?: boolean }) {
  const [playing, setPlaying] = useState(false);
  const [loading, setLoading] = useState(false);
  const audio = useRef<HTMLAudioElement | null>(null);
  const src = api.mediaUrl(url);
  const canSpeak = !src && !!text && typeof window !== "undefined" && "speechSynthesis" in window;

  function stop() {
    audio.current?.pause();
    if (canSpeak) window.speechSynthesis.cancel();
    setPlaying(false);
    setLoading(false);
  }

  function play() {
    if (src) {
      const a = audio.current ?? new window.Audio(src);
      audio.current = a;
      a.onended = () => setPlaying(false);
      // Loading until audio actually starts (the clip is fetched on first play).
      a.onwaiting = () => setLoading(true);
      a.onplaying = () => {
        setLoading(false);
        setPlaying(true);
      };
      a.currentTime = 0;
      setLoading(true);
      a.play().catch(() => {
        setLoading(false);
        setPlaying(false);
      });
    } else if (canSpeak && text) {
      window.speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(text);
      u.onstart = () => {
        setLoading(false);
        setPlaying(true);
      };
      u.onend = () => setPlaying(false);
      u.onerror = () => {
        setLoading(false);
        setPlaying(false);
      };
      setLoading(true);
      window.speechSynthesis.speak(u);
    }
  }

  const playRef = useRef(play);
  useEffect(() => {
    playRef.current = play;
  });
  useEffect(() => {
    if (autoPlay && src) playRef.current();
    return () => audio.current?.pause();
  }, [autoPlay, src]);

  if (!src && !canSpeak) return null;
  return (
    <button
      onClick={playing || loading ? stop : play}
      aria-busy={loading}
      aria-label={loading ? "Loading audio, click to cancel" : undefined}
      className="inline-flex items-center gap-1.5 rounded-full border border-line bg-surface px-3 py-1 text-xs font-medium text-ink transition hover:bg-hover"
    >
      {loading ? (
        <span className="h-3.5 w-3.5 animate-spin rounded-full border-[1.75px] border-current border-t-transparent opacity-70" aria-hidden="true" />
      ) : playing ? (
        <IconPause className="h-3.5 w-3.5" />
      ) : (
        <IconPlay className="h-3.5 w-3.5" />
      )}
      {loading ? "Loading" : playing ? "Stop" : label}
    </button>
  );
}

/** Icon for an access level: lock (senior only), key (successor), people (team). */
export function ScopeIcon({ scope, className = "h-3 w-3" }: { scope: MemoryScope; className?: string }) {
  if (scope === "never_transfer") return <IconLock className={className} />;
  if (scope === "successor") return <IconKey className={className} />;
  return <IconUsers className={className} />;
}

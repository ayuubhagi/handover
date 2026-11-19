"use client";

import { useEffect, useRef, useState } from "react";
import { IconArrowUp, IconPhone } from "./icons";
import { Menu } from "./Menu";
import type { Mode } from "./store";

const MODES: { value: Mode; label: string; icon: React.ReactNode }[] = [
  { value: "interview", label: "Record", icon: <ModeGlyph mode="interview" /> },
  { value: "ask", label: "Ask", icon: <ModeGlyph mode="ask" /> },
];

function ModeGlyph({ mode }: { mode: Mode }) {
  // Three little bars, like a level meter. Orange for recording, teal for asking.
  const c = mode === "interview" ? "bg-accent" : "bg-[#78d6d2]";
  return (
    <span className="flex h-3 items-end gap-[2px]" aria-hidden="true">
      <span className={`w-[3px] rounded-[1px] ${c}`} style={{ height: "55%" }} />
      <span className={`w-[3px] rounded-[1px] ${c}`} style={{ height: "100%" }} />
      <span className={`w-[3px] rounded-[1px] ${c} opacity-70`} style={{ height: "70%" }} />
    </span>
  );
}

export function Composer({
  placeholder,
  disabled,
  mode,
  onMode,
  onSend,
  recording,
  level,
  onCall,
  autoFocus,
}: {
  placeholder: string;
  disabled?: boolean;
  mode: Mode;
  /** Omit to hide the mode switch (ask-only viewers). */
  onMode?: (m: Mode) => void;
  /** Resolve to null or false when sending failed: the text is put back so nothing typed is lost. */
  onSend: (text: string) => unknown;
  recording?: boolean;
  level?: number;
  onCall?: () => void;
  autoFocus?: boolean;
}) {
  const [text, setText] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "0px";
    el.style.height = `${Math.min(el.scrollHeight, 180)}px`;
  }, [text]);

  async function submit() {
    const t = text.trim();
    if (!t || disabled) return;
    setText("");
    const result = await onSend(t);
    if (result === null || result === false) setText((current) => current || t);
  }

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
      className="composer rounded-2xl border border-line-strong/70 shadow-[var(--shadow-pop)]"
    >
      <div className="px-4 pt-3.5">
        {recording ? (
          <div className="flex min-h-12 items-center gap-3 text-sm text-muted" aria-live="polite">
            <span className="h-2 w-2 animate-pulse rounded-full bg-accent" />
            Listening
            <Bars level={level ?? 0} />
          </div>
        ) : (
          <textarea
            ref={ref}
            rows={1}
            value={text}
            autoFocus={autoFocus}
            aria-label={placeholder}
            placeholder={placeholder}
            disabled={disabled}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit();
              }
            }}
            className="block max-h-[180px] min-h-12 w-full resize-none bg-transparent text-[15px] leading-6 placeholder:text-soft disabled:opacity-60"
          />
        )}
      </div>
      <div className="flex items-center gap-1 px-2 pb-2 pt-1">
        {onMode && <Menu label="Mode" value={mode} onChange={onMode} options={MODES} placement="top-start" />}
        <div className="ml-auto flex items-center gap-1">
          {onCall && !recording && (
            <button
              type="button"
              onClick={onCall}
              disabled={disabled}
              className="flex h-8 items-center gap-1.5 rounded-full bg-accent px-3.5 text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-40"
            >
              <IconPhone className="h-4 w-4" />
              Call
            </button>
          )}
          {!recording && (
            <button
              type="submit"
              disabled={disabled || !text.trim()}
              aria-label="Send"
              className="grid h-8 w-8 place-items-center rounded-lg bg-primary text-on-primary transition hover:opacity-90 disabled:bg-hover disabled:text-soft"
            >
              <IconArrowUp />
            </button>
          )}
        </div>
      </div>
    </form>
  );
}

export function Bars({ level, count = 18, className = "h-5" }: { level: number; count?: number; className?: string }) {
  return (
    <span className={`flex items-center gap-[3px] ${className}`} aria-hidden="true">
      {Array.from({ length: count }, (_, i) => {
        const shape = 0.35 + 0.65 * Math.abs(Math.sin(i * 1.7 + level * 9));
        const h = Math.max(0.12, Math.min(1, level * 1.6 * shape + 0.1));
        return <span key={i} className="w-[3px] rounded-full bg-accent transition-[height] duration-75" style={{ height: `${h * 100}%` }} />;
      })}
    </span>
  );
}

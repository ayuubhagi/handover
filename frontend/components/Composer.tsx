"use client";

import { useEffect, useRef, useState } from "react";
import { IconArrowUp, IconMic, IconPhone, IconStop } from "./icons";

export function Composer({
  placeholder,
  disabled,
  onSend,
  onMicStart,
  onMicStop,
  recording,
  level,
  onCall,
  autoFocus,
}: {
  placeholder: string;
  disabled?: boolean;
  onSend: (text: string) => void;
  onMicStart?: () => void;
  onMicStop?: () => void;
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

  function submit() {
    const t = text.trim();
    if (!t || disabled) return;
    onSend(t);
    setText("");
  }

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
      className="glass flex items-end gap-2 rounded-[26px] border border-line p-2 pl-5 shadow-[var(--shadow-pop)]"
    >
      {recording ? (
        <div className="flex min-h-10 flex-1 items-center gap-3 text-sm text-muted" aria-live="polite">
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
          className="max-h-[180px] min-h-10 flex-1 resize-none bg-transparent py-2.5 text-[15px] leading-5 placeholder:text-soft disabled:opacity-60"
        />
      )}
      {onCall && !recording && (
        <button type="button" onClick={onCall} disabled={disabled} aria-label="Start a voice call" className="grid h-10 w-10 place-items-center rounded-full text-muted transition hover:bg-hover hover:text-ink disabled:opacity-40">
          <IconPhone className="h-[18px] w-[18px]" />
        </button>
      )}
      {onMicStart && (
        <button
          type="button"
          onClick={recording ? onMicStop : onMicStart}
          disabled={disabled && !recording}
          aria-label={recording ? "Stop and send" : "Answer by voice"}
          className={`grid h-10 w-10 place-items-center rounded-full transition disabled:opacity-40 ${recording ? "bg-accent text-on-accent" : "text-muted hover:bg-hover hover:text-ink"}`}
        >
          {recording ? <IconStop className="h-[18px] w-[18px]" /> : <IconMic className="h-[18px] w-[18px]" />}
        </button>
      )}
      {!recording && (
        <button
          type="submit"
          disabled={disabled || !text.trim()}
          aria-label="Send"
          className="grid h-10 w-10 place-items-center rounded-full bg-primary text-on-primary transition hover:opacity-90 disabled:opacity-25"
        >
          <IconArrowUp className="h-[18px] w-[18px]" />
        </button>
      )}
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

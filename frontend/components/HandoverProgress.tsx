"use client";

import { useId, useState } from "react";
import { api } from "../lib/api";
import { useLive, useLoad } from "../lib/hooks";
import type { Gap } from "../lib/types";
import { IconCheck, IconChevron } from "./icons";

/** Planned number of handover interviews (one a day). */
export const PLANNED_SESSIONS = 4;

/** Dana's handover state: current session, captured memories, open gaps. Refreshes on live memory changes. */
function useHandoverProgress(refreshKey: number) {
  const mems = useLoad(() => api.listMemories("u_expert"), [refreshKey]);
  const gaps = useLoad(() => api.gaps("u_expert"), [refreshKey]);
  useLive((e) => {
    if (e.type !== "memory_changed") return;
    mems.reload();
    gaps.reload();
  });

  if (!mems.data || !gaps.data) return null;
  const sessionsDone = new Set(mems.data.map((m) => m.session_id).filter(Boolean)).size;
  return {
    session: Math.min(sessionsDone + 1, PLANNED_SESSIONS),
    captured: mems.data.filter((m) => m.status === "active").length,
    open: gaps.data.filter((g) => g.status !== "answered"),
  };
}

const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;

/** Dana's handover at a glance: session track, what's captured, and what's still uncovered. */
export function HandoverProgress({ refreshKey = 0 }: { refreshKey?: number }) {
  const p = useHandoverProgress(refreshKey);
  const [open, setOpen] = useState(false);
  const listId = useId();
  if (!p) return null;

  const hasGaps = p.open.length > 0;

  return (
    <section aria-label="Handover progress" className="glass mx-auto w-full max-w-2xl rounded-2xl border border-line">
      <div className="flex items-center gap-4 px-4 py-3">
        <div className="min-w-0 flex-1">
          <p className="text-xs font-medium uppercase tracking-wide text-soft">Handover</p>
          <p className="mt-0.5 text-sm font-medium text-ink">
            Session {p.session} <span className="text-muted">of {PLANNED_SESSIONS}</span>
          </p>
          <SessionTrack current={p.session} />
        </div>

        <Stat value={p.captured} label={p.captured === 1 ? "memory" : "memories"} />

        {hasGaps ? (
          <button
            type="button"
            onClick={() => setOpen((o) => !o)}
            aria-expanded={open}
            aria-controls={listId}
            className="-my-1 flex items-center gap-1 rounded-xl px-2 py-1 transition hover:bg-hover"
          >
            <Stat value={p.open.length} label={p.open.length === 1 ? "open gap" : "open gaps"} tone="accent" />
            <IconChevron className={`h-4 w-4 text-soft transition ${open ? "rotate-180" : ""}`} />
          </button>
        ) : (
          <span className="flex items-center gap-1.5 text-sm text-ok">
            <IconCheck className="h-4 w-4" /> No gaps
          </span>
        )}
      </div>

      {open && hasGaps && <GapList id={listId} gaps={p.open} />}
    </section>
  );
}

function SessionTrack({ current }: { current: number }) {
  return (
    <div className="mt-2 flex max-w-48 gap-1" aria-hidden>
      {Array.from({ length: PLANNED_SESSIONS }, (_, i) => (
        <span
          key={i}
          className={`h-1 flex-1 rounded-full ${i < current - 1 ? "bg-accent" : i === current - 1 ? "bg-accent/50" : "bg-line"}`}
        />
      ))}
    </div>
  );
}

function Stat({ value, label, tone }: { value: number; label: string; tone?: "accent" }) {
  return (
    <span className="flex flex-col items-end leading-tight">
      <span className={`font-serif text-xl tabular-nums ${tone === "accent" ? "text-accent-ink" : "text-ink"}`}>{value}</span>
      <span className="text-xs text-muted">{label}</span>
    </span>
  );
}

function GapList({ id, gaps }: { id: string; gaps: Gap[] }) {
  return (
    <div id={id} className="border-t border-line px-4 py-3">
      <p className="mb-2 text-xs text-muted">{plural(gaps.length, "question", "questions")} Dana hasn’t covered yet</p>
      <ol className="space-y-1.5 text-sm text-ink">
        {gaps.map((g) => (
          <li key={g.id} className="flex gap-2.5">
            <span className="mt-[7px] h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
            <span>{g.question}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}

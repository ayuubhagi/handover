"use client";

import { useState } from "react";
import { api } from "../lib/api";
import { useLive, useLoad } from "../lib/hooks";
import { IconChevron, IconCircle } from "./icons";

/** Planned number of handover interviews (one a day). */
export const PLANNED_SESSIONS = 4;

/** Dana's handover progress: which session she is on, what is captured, and the open gaps left to cover. */
export function HandoverProgress({ refreshKey = 0 }: { refreshKey?: number }) {
  const mems = useLoad(() => api.listMemories("u_expert"), [refreshKey]);
  const gaps = useLoad(() => api.gaps("u_expert"), [refreshKey]);
  const [open, setOpen] = useState(false);
  useLive((e) => {
    if (e.type === "memory_changed") {
      mems.reload();
      gaps.reload();
    }
  });

  if (!mems.data || !gaps.data) return null;
  const active = mems.data.filter((m) => m.status === "active");
  const done = new Set(mems.data.map((m) => m.session_id).filter(Boolean)).size;
  const session = Math.min(done + 1, PLANNED_SESSIONS);
  const todo = gaps.data.filter((g) => g.status !== "answered");

  return (
    <div className="glass mx-auto w-full max-w-2xl rounded-2xl border border-line text-sm">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        disabled={todo.length === 0}
        className="flex w-full flex-wrap items-center gap-x-4 gap-y-1 px-4 py-2.5 text-left"
      >
        <span className="font-medium text-ink">
          Session {session} of {PLANNED_SESSIONS}
        </span>
        <span className="text-muted">
          {active.length} {active.length === 1 ? "memory" : "memories"} captured
        </span>
        <span className="text-muted">
          {todo.length === 0 ? "No open gaps" : `${todo.length} open ${todo.length === 1 ? "gap" : "gaps"} to cover`}
        </span>
        {todo.length > 0 && <IconChevron className={`ml-auto h-4 w-4 text-soft transition ${open ? "rotate-180" : ""}`} />}
      </button>
      {open && todo.length > 0 && (
        <ul className="space-y-2 border-t border-line px-4 py-3">
          {todo.map((g) => (
            <li key={g.id} className="flex gap-2 text-ink">
              <IconCircle className="mt-1 h-3 w-3 shrink-0 text-accent" />
              <span>{g.question}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

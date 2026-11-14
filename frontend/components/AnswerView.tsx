"use client";

import type { AskResponse } from "../lib/types";
import { MemoryMeta, PlayButton } from "./ui";

export function AnswerView({ r }: { r: AskResponse }) {
  return (
    <div className="space-y-4">
      {r.blocked_count > 0 && (
        <div role="status" className="rounded-lg border border-danger/25 bg-danger-soft px-4 py-3 text-sm text-danger">
          {r.blocked_count} {r.blocked_count === 1 ? "memory matched" : "memories matched"} but {r.blocked_count === 1 ? "is" : "are"} outside your scope, so {r.blocked_count === 1 ? "it was" : "they were"} withheld. This was logged.
        </div>
      )}
      <p className="font-serif text-lg leading-relaxed">{r.answer_text}</p>
      {r.sources.length > 0 && (
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">In Dana’s words</p>
          <ul className="space-y-3">
            {r.sources.map((s) => (
              <li key={s.memory.id} className="rounded-lg border border-line p-3">
                {s.transcript && <p className="text-sm italic">“{s.transcript}”</p>}
                <div className="mt-2">
                  <PlayButton url={s.clip_url} text={s.transcript ?? undefined} label={`Play ${s.memory.source_clip_id}`} />
                </div>
                <div className="mt-2">
                  <MemoryMeta m={s.memory} />
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
      <p className="font-mono text-[11px] text-muted">audit {r.audit_id}</p>
    </div>
  );
}

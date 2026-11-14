"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api, errorMessage } from "../lib/api";
import { useLive, useUserId } from "../lib/hooks";
import type { RunbookStep } from "../lib/types";
import { Card, ErrorNote, Loading } from "./ui";

type Shown = RunbookStep & { leaving?: boolean; fresh?: boolean };

export function Runbook({ simple = false }: { simple?: boolean }) {
  const user = useUserId();
  const [steps, setSteps] = useState<Shown[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);

  const load = useCallback(async (animate: boolean) => {
    try {
      const next = await api.runbook();
      setError(null);
      setSteps((prev) => {
        if (!prev || !animate) return next;
        const ids = new Set(next.map((s) => s.id));
        const prevIds = new Set(prev.map((s) => s.id));
        // Keep removed steps in place, flagged, so they can animate out.
        const merged: Shown[] = [];
        for (const p of prev) {
          if (ids.has(p.id)) merged.push({ ...next.find((s) => s.id === p.id)! });
          else if (!p.leaving) merged.push({ ...p, leaving: true });
          else merged.push(p);
        }
        for (const s of next) if (!prevIds.has(s.id)) merged.push({ ...s, fresh: true });
        return merged;
      });
      timers.current.push(setTimeout(() => setSteps((s) => s?.filter((x) => !x.leaving) ?? s), 1700));
    } catch (e) {
      setError(errorMessage(e));
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load(false);
  }, [load, user]);
  useEffect(() => () => timers.current.forEach(clearTimeout), []);

  const live = useLive((e) => {
    if (e.type === "runbook_changed" || e.type === "memory_changed") load(true);
  });

  return (
    <Card
      title={simple ? "Checklist" : "Runbook"}
      aside={
        <span className="flex items-center gap-1.5 text-xs text-muted">
          <span className={`h-2 w-2 rounded-full ${live ? "bg-accent" : "bg-line"}`} />
          {live ? "Live" : "Reconnecting"}
        </span>
      }
    >
      <p className="mb-4 text-xs text-muted">{simple ? "Built from what was handed over. A step goes away when the thing behind it is forgotten." : "Built from the handed-over memories. Steps disappear here when the memory behind them is forgotten."}</p>
      {error && <ErrorNote message={error} onRetry={() => load(false)} />}
      {!steps && !error && <Loading label="Loading runbook" />}
      {steps?.length === 0 && <p className="text-sm text-muted">No steps visible to you.</p>}
      <ol className="space-y-2">
        {steps?.map((s, i) => (
          <li
            key={s.id}
            className={`flex gap-3 rounded-lg border border-line px-3 py-2.5 ${s.leaving ? "step-leaving" : s.fresh ? "step-enter" : ""}`}
          >
            <span className="mt-0.5 w-5 shrink-0 text-right font-mono text-xs text-muted">{i + 1}</span>
            <div>
              <p className="text-sm">{s.text}</p>
              {simple ? (
                (s.status === "needs_review" || s.leaving) && (
                  <p className="mt-1 text-xs font-medium">
                    {s.leaving ? <span className="text-danger">Removed</span> : <span className="text-warn">Needs a check</span>}
                  </p>
                )
              ) : (
<p className="mt-1 font-mono text-[11px] text-muted">
                {s.id} from {s.derived_from.join(", ")}
                {s.status === "needs_review" && !s.leaving && <span className="ml-2 font-sans font-medium text-warn">needs review</span>}
                {s.leaving && <span className="ml-2 font-sans font-medium text-danger">removed</span>}
              </p>
              )}
            </div>
          </li>
        ))}
      </ol>
    </Card>
  );
}

"use client";

import { useState } from "react";
import { AuditLog } from "../../components/AuditLog";
import { Compare } from "../../components/Compare";
import { MemoryList } from "../../components/MemoryList";
import { Runbook } from "../../components/Runbook";
import { Card, ErrorNote, Loading, Tag } from "../../components/ui";
import { api } from "../../lib/api";
import { API_URL, DEMO_MODE, USE_MOCKS } from "../../lib/config";
import { useLive, useLoad, useUserId } from "../../lib/hooks";
import type { LiveEvent } from "../../lib/types";


/** Public demo only: restore the fictional data after visitors have forgotten or corrected things. */
function ResetDemo({ onDone }: { onDone: () => void }) {
  const [state, setState] = useState<"idle" | "busy" | "done" | string>("idle");
  async function reset() {
    setState("busy");
    try {
      const res = await fetch(`${API_URL}/demo/reset`, { method: "POST" });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(body?.detail ?? res.statusText);
      setState("done");
      onDone();
    } catch (e) {
      setState(e instanceof Error ? e.message : "Reset failed");
    }
  }
  return (
    <button
      type="button"
      onClick={reset}
      disabled={state === "busy"}
      className="rounded-full border border-line px-2.5 py-1 font-medium text-muted hover:text-ink disabled:opacity-60"
      title="Restores the fictional demo data for everyone"
    >
      {state === "busy" ? "Resetting" : state === "done" ? "Demo data restored" : state === "idle" ? "Reset demo data" : state}
    </button>
  );
}

export default function UnderTheHood() {
  const user = useUserId();
  const mems = useLoad(() => api.listMemories("u_expert"));
  const gaps = useLoad(() => api.gaps("u_expert"));
  const [events, setEvents] = useState<{ at: string; e: LiveEvent }[]>([]);
  const connected = useLive((e) => {
    setEvents((all) => [{ at: new Date().toLocaleTimeString(), e }, ...all].slice(0, 50));
    if (e.type === "memory_changed") {
      mems.reload();
      gaps.reload();
    }
  });

  return (
    <div className="h-full overflow-y-auto px-4 pb-16 pt-14 md:pt-10">
      <div className="mx-auto max-w-5xl">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="font-serif text-3xl tracking-tight sm:text-4xl">Under the hood</h1>
            
          </div>
          <div className="flex items-center gap-2 text-xs">
            {DEMO_MODE && !USE_MOCKS && (
              <ResetDemo
                onDone={() => {
                  mems.reload();
                  gaps.reload();
                }}
              />
            )}
            <span className={`rounded-full px-2.5 py-1 font-medium ${USE_MOCKS ? "bg-warn-soft text-warn" : "bg-ok-soft text-ok"}`}>{USE_MOCKS ? "Mock data" : `API ${API_URL}`}</span>
            <span className="flex items-center gap-1.5 text-muted">
              <span className={`h-2 w-2 rounded-full ${connected ? "bg-ok" : "bg-line-strong"}`} />
              {connected ? "WS /live connected" : "WS reconnecting"}
            </span>
          </div>
        </div>

        <div className="mt-8 space-y-6">
          {<MemoryList memories={mems.data} loading={mems.loading} error={mems.error} reload={mems.reload} canEdit={user === "u_expert"} />}
          {(
            <Card title="Gaps and contradictions">
              {gaps.error && <ErrorNote message={gaps.error} onRetry={gaps.reload} />}
              {gaps.loading && !gaps.data && <Loading />}
              {gaps.data?.length === 0 && <p className="text-sm text-muted">No gaps.</p>}
              <ul className="space-y-2">
                {gaps.data?.map((g) => (
                  <li key={g.id} className="rounded-xl border border-line p-3 text-sm">
                    <div className="mb-1 flex flex-wrap items-center gap-2">
                      <Tag tone={g.kind === "contradiction" ? "never_transfer" : "neutral"}>{g.kind}</Tag>
                      <Tag>{g.status}</Tag>
                      <span className="font-mono text-xs text-muted">{g.id} from {g.from_memory_ids.join(", ") || "none"}</span>
                    </div>
                    {g.question}
                  </li>
                ))}
              </ul>
            </Card>
          )}
          {<Runbook />}
          {<AuditLog />}
          {<Compare />}
          {(
            <Card title="WS /live events">
              {events.length === 0 && <p className="text-sm text-muted">Waiting for changes. Answer, fix or forget something to see events.</p>}
              <ul className="space-y-1.5 font-mono text-xs">
                {events.map((x, i) => (
                  <li key={i} className="flex gap-3">
                    <span className="text-soft">{x.at}</span>
                    <span className="text-accent-ink">{x.e.type}</span>
                    {x.e.type === "memory_changed" && (
                      <span className="text-muted">
                        {x.e.memory.id} {x.e.memory.status} {x.e.memory.scope} v{x.e.memory.version}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

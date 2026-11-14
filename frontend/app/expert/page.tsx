"use client";

import { Interview } from "../../components/Interview";
import { MemoryList } from "../../components/MemoryList";
import { Card, ErrorNote, Loading, Tag } from "../../components/ui";
import { api } from "../../lib/api";
import { useLive, useLoad, useUserId } from "../../lib/hooks";

export default function ExpertPage() {
  const user = useUserId();
  const memories = useLoad(() => api.listMemories("u_expert"));
  const gaps = useLoad(() => api.gaps("u_expert"));
  useLive(() => {
    memories.reload();
    gaps.reload();
  });
  const refresh = () => {
    memories.reload();
    gaps.reload();
  };

  return (
    <div>
      <div className="mb-8 max-w-2xl">
        <h1 className="font-serif text-3xl tracking-tight">Dana’s handover</h1>
        <p className="mt-2 text-muted">Answer the interviewer, then decide who inherits each memory, correct what is wrong, and forget what should not be passed on.</p>
      </div>
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]">
        <div className="space-y-6">
          {user === "u_expert" ? (
            <Interview onChange={refresh} />
          ) : (
            <Card title="Interview">
              <p className="text-sm text-muted">Only Dana can run her interview. Switch to Dana in the header.</p>
            </Card>
          )}
          <Card title="Gaps the agent is chasing">
            {gaps.error && <ErrorNote message={gaps.error} onRetry={gaps.reload} />}
            {gaps.loading && !gaps.data && <Loading />}
            {gaps.data?.length === 0 && <p className="text-sm text-muted">No gaps found yet.</p>}
            <ul className="space-y-3">
              {gaps.data?.map((g) => (
                <li key={g.id} className={`rounded-lg border p-3 text-sm ${g.kind === "contradiction" ? "border-warn/30 bg-warn-soft" : "border-line"}`}>
                  <div className="mb-1 flex items-center gap-2 text-xs">
                    <Tag>{g.kind}</Tag>
                    <span className="text-muted">{g.status}</span>
                    {g.from_memory_ids.length > 0 && <span className="font-mono text-muted">from {g.from_memory_ids.join(", ")}</span>}
                  </div>
                  <p className={g.status === "answered" ? "text-muted line-through" : ""}>{g.question}</p>
                </li>
              ))}
            </ul>
          </Card>
        </div>
        <MemoryList memories={memories.data} loading={memories.loading} error={memories.error} reload={memories.reload} canEdit={user === "u_expert"} />
      </div>
    </div>
  );
}

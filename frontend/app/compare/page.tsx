"use client";

import { useState } from "react";
import { AnswerView } from "../../components/AnswerView";
import { Button, Card, ErrorNote, Loading } from "../../components/ui";
import { api, errorMessage } from "../../lib/api";
import type { AskResponse } from "../../lib/types";

type Side = { r: AskResponse | null; error: string | null };

export default function ComparePage() {
  const [q, setQ] = useState("When should I restart the payments queue?");
  const [busy, setBusy] = useState(false);
  const [on, setOn] = useState<Side>({ r: null, error: null });
  const [off, setOff] = useState<Side>({ r: null, error: null });

  async function run() {
    if (!q.trim()) return;
    setBusy(true);
    const [a, b] = await Promise.allSettled([api.ask(q.trim(), true), api.ask(q.trim(), false)]);
    setOn(a.status === "fulfilled" ? { r: a.value, error: null } : { r: null, error: errorMessage(a.reason) });
    setOff(b.status === "fulfilled" ? { r: b.value, error: null } : { r: null, error: errorMessage(b.reason) });
    setBusy(false);
  }

  const panel = (title: string, side: Side) => (
    <Card title={title}>
      {busy && <Loading label="Asking" />}
      {!busy && side.error && <ErrorNote message={side.error} />}
      {!busy && side.r && <AnswerView r={side.r} />}
      {!busy && !side.r && !side.error && <p className="text-sm text-muted">Ask a question to compare.</p>}
    </Card>
  );

  return (
    <div>
      <div className="mb-8 max-w-2xl">
        <h1 className="font-serif text-3xl tracking-tight">Memory on vs off</h1>
        <p className="mt-2 text-muted">The same question, with and without Dana’s governed memories.</p>
      </div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          run();
        }}
        className="mb-6 flex gap-2"
      >
        <input aria-label="Question" value={q} onChange={(e) => setQ(e.target.value)} className="min-w-0 flex-1 rounded-lg border border-line bg-surface px-3 py-2 text-sm focus:outline-2 focus:outline-accent" />
        <Button type="submit" disabled={busy || !q.trim()}>Compare</Button>
      </form>
      <div className="grid gap-6 md:grid-cols-2">
        {panel("Memory on", on)}
        {panel("Memory off", off)}
      </div>
    </div>
  );
}

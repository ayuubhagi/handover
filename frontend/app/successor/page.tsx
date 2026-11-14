"use client";

import { useState } from "react";
import { AnswerView } from "../../components/AnswerView";
import { Runbook } from "../../components/Runbook";
import { Button, Card, ErrorNote, Loading } from "../../components/ui";
import { api, errorMessage } from "../../lib/api";
import { useUserId } from "../../lib/hooks";
import { personName, type AskResponse } from "../../lib/types";

const SUGGESTIONS = [
  "What do I do when SWIFT messages are stuck?",
  "When should I restart the payments queue?",
  "Anything odd about the Northwind Freight file?",
];

export default function SuccessorPage() {
  const user = useUserId();
  const [q, setQ] = useState("");
  const [result, setResult] = useState<AskResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function ask(question: string) {
    if (!question.trim()) return;
    setQ(question);
    setBusy(true);
    setError(null);
    try {
      setResult(await api.ask(question.trim(), true));
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <div className="mb-8 max-w-2xl">
        <h1 className="font-serif text-3xl tracking-tight">Ask Dana</h1>
        <p className="mt-2 text-muted">
          Asking as <span className="font-medium text-ink">{personName(user)}</span>. Answers only use memories you are allowed to inherit, and play Dana’s own recording.
        </p>
      </div>
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
        <Card title="Question">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              ask(q);
            }}
            className="flex gap-2"
          >
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="What do I do when…"
              className="min-w-0 flex-1 rounded-lg border border-line bg-surface px-3 py-2 text-sm focus:outline-2 focus:outline-accent"
            />
            <Button type="submit" disabled={busy || !q.trim()}>Ask</Button>
          </form>
          <div className="mt-3 flex flex-wrap gap-2">
            {SUGGESTIONS.map((s) => (
              <button key={s} onClick={() => ask(s)} className="rounded-full border border-line px-3 py-1 text-xs text-muted hover:border-accent/40 hover:text-ink">
                {s}
              </button>
            ))}
          </div>
          <div className="mt-6">
            {busy && <Loading label="Thinking" />}
            {error && <ErrorNote message={error} />}
            {!busy && result && <AnswerView r={result} />}
          </div>
        </Card>
        <Runbook />
      </div>
    </div>
  );
}

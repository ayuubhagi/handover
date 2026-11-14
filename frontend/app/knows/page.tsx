"use client";

import { useState } from "react";
import { Runbook } from "../../components/Runbook";
import { AUDIENCE, ErrorNote, Loading } from "../../components/ui";
import { api, errorMessage } from "../../lib/api";
import { useLive, useLoad, useUserId } from "../../lib/hooks";
import type { Memory, MemoryScope } from "../../lib/types";

export default function KnowsPage() {
  const user = useUserId();
  const mems = useLoad(() => api.listMemories("u_expert"));
  useLive((e) => {
    if (e.type === "memory_changed") mems.reload();
  });
  const list = (mems.data ?? []).filter((m) => m.status === "active");
  const canEdit = user === "u_expert";

  return (
    <div className="h-full overflow-y-auto px-4 pb-16 pt-14 md:pt-10">
      <div className="mx-auto max-w-5xl">
        <h1 className="font-serif text-3xl tracking-tight sm:text-4xl">Handed over</h1>
        <p className="mt-2 max-w-xl text-muted">
          {canEdit ? "Everything you’ve shared so far. Choose who can see each one, fix it, or forget it." : "What has been handed over that you can see."}
        </p>
        <div className="mt-8 grid gap-6 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
          <div>
            {mems.error && <ErrorNote message={mems.error} onRetry={mems.reload} />}
            {mems.loading && !mems.data && <Loading />}
            {mems.data && list.length === 0 && <p className="text-sm text-muted">Nothing here yet.</p>}
            <ul className="space-y-3">
              {list.map((m) => (
                <Item key={m.id} m={m} canEdit={canEdit} onDone={mems.reload} />
              ))}
            </ul>
          </div>
          <div>
            <Runbook simple />
          </div>
        </div>
      </div>
    </div>
  );
}

function Item({ m, canEdit, onDone }: { m: Memory; canEdit: boolean; onDone: () => void }) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(m.text);
  const [confirm, setConfirm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(fn: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await fn();
      onDone();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <li className="rounded-2xl border border-line bg-surface p-4">
      {editing ? (
        <div className="space-y-2">
          <textarea aria-label="Fix this" value={text} onChange={(e) => setText(e.target.value)} rows={3} className="w-full rounded-xl border border-line bg-bg p-3 text-[15px]" />
          <div className="flex gap-2">
            <button
              onClick={() => run(async () => { await api.correct(m.id, text.trim()); setEditing(false); })}
              disabled={busy || !text.trim() || text.trim() === m.text}
              className="rounded-full bg-primary px-4 py-1.5 text-sm font-medium text-on-primary disabled:opacity-40"
            >
              Save
            </button>
            <button onClick={() => { setEditing(false); setText(m.text); }} className="rounded-full px-3 py-1.5 text-sm text-muted hover:bg-hover">
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <p className="text-[15px] leading-relaxed">{m.text}</p>
      )}
      {canEdit && !editing && (
        <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-xs text-muted">
            Who can see this
            <div role="radiogroup" aria-label="Who can see this" className="flex rounded-full bg-hover p-0.5">
              {AUDIENCE.map((a) => (
                <button
                  key={a.value}
                  role="radio"
                  aria-checked={m.scope === a.value}
                  disabled={busy}
                  onClick={() => m.scope !== a.value && run(() => api.setScope(m.id, a.value as MemoryScope))}
                  className={`rounded-full px-2.5 py-1 font-medium transition ${m.scope === a.value ? "bg-surface text-ink shadow-sm" : "text-muted hover:text-ink"}`}
                >
                  {a.label}
                </button>
              ))}
            </div>
          </div>
          <div className="flex items-center gap-1 text-sm">
            <button onClick={() => setEditing(true)} className="rounded-full px-3 py-1 text-muted hover:bg-hover hover:text-ink">
              Fix
            </button>
            {confirm ? (
              <span className="flex items-center gap-1">
                <span className="px-1 text-danger">Forget for good?</span>
                <button onClick={() => run(() => api.forget(m.id))} disabled={busy} className="rounded-full bg-danger px-3 py-1 font-medium text-white">
                  Forget
                </button>
                <button onClick={() => setConfirm(false)} className="rounded-full px-3 py-1 text-muted hover:bg-hover">
                  Keep
                </button>
              </span>
            ) : (
              <button onClick={() => setConfirm(true)} className="rounded-full px-3 py-1 text-danger hover:bg-danger-soft">
                Forget
              </button>
            )}
          </div>
        </div>
      )}
      {error && <div className="mt-2"><ErrorNote message={error} /></div>}
    </li>
  );
}

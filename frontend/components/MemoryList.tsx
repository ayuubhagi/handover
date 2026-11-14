"use client";

import { useState } from "react";
import { api, errorMessage } from "../lib/api";
import type { Memory, MemoryScope } from "../lib/types";
import { Button, Card, ErrorNote, Loading, MemoryMeta } from "./ui";

type Notice = { id: string; tone: "ok" | "warn"; text: string };

export function MemoryList({
  memories,
  loading,
  error,
  reload,
  canEdit,
}: {
  memories: Memory[] | null;
  loading: boolean;
  error: string | null;
  reload: () => void;
  canEdit: boolean;
}) {
  const [showInactive, setShowInactive] = useState(false);
  const [notices, setNotices] = useState<Notice[]>([]);
  const note = (n: Notice) => setNotices((all) => [n, ...all.filter((x) => x.id !== n.id)].slice(0, 4));

  const list = (memories ?? []).filter((m) => showInactive || m.status === "active");

  return (
    <Card
      title="Memories"
      aside={
        <label className="flex items-center gap-2 text-xs text-muted">
          <input type="checkbox" checked={showInactive} onChange={(e) => setShowInactive(e.target.checked)} />
          Show corrected and forgotten
        </label>
      }
    >
      {!canEdit && <p className="mb-3 text-xs text-muted">Only the person handing over can change these. Switch roles (top right) to edit.</p>}
      {notices.map((n) => (
        <div key={n.id} className={`mb-3 rounded-md px-3 py-2 text-sm ${n.tone === "warn" ? "bg-danger-soft text-danger" : "bg-accent-soft text-accent"}`}>
          {n.text}
        </div>
      ))}
      {error && <ErrorNote message={error} onRetry={reload} />}
      {loading && !memories && <Loading label="Loading memories" />}
      {memories && list.length === 0 && <p className="text-sm text-muted">No memories yet.</p>}
      <ul className="space-y-3">
        {list.map((m) => (
          <MemoryRow key={m.id} m={m} canEdit={canEdit && m.status === "active"} onDone={reload} note={note} />
        ))}
      </ul>
    </Card>
  );
}

function MemoryRow({ m, canEdit, onDone, note }: { m: Memory; canEdit: boolean; onDone: () => void; note: (n: Notice) => void }) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(m.text);
  const [confirmForget, setConfirmForget] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(fn: () => Promise<void>) {
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

  const changeScope = (scope: MemoryScope) =>
    run(async () => {
      const r = await api.setScope(m.id, scope);
      note({ id: m.id, tone: "ok", text: `${m.id} is now scoped to ${r.scope.replace("_", " ")}.` });
    });

  const correct = () =>
    run(async () => {
      const r = await api.correct(m.id, text.trim());
      setEditing(false);
      note({ id: m.id, tone: "ok", text: `Corrected: ${r.old.id} v${r.old.version} is superseded by ${r.new.id} v${r.new.version}.` });
    });

  const forget = () =>
    run(async () => {
      const r = await api.forget(m.id);
      setConfirmForget(false);
      const steps = r.runbook_steps_removed.length ? `Runbook steps removed: ${r.runbook_steps_removed.join(", ")}.` : "No runbook steps depended on it.";
      note({ id: m.id, tone: "warn", text: `Forgot ${r.forgotten_ids.join(", ")}. ${steps} Audit ${r.audit_id}.` });
    });

  const inactive = m.status !== "active";

  return (
    <li className={`rounded-lg border border-line p-4 ${inactive ? "opacity-60" : ""}`}>
      {editing ? (
        <div className="space-y-2">
          <textarea aria-label="Corrected memory text" value={text} onChange={(e) => setText(e.target.value)} rows={3} className="w-full rounded-md border border-line p-2 text-sm focus:outline-2 focus:outline-accent" />
          <div className="flex gap-2">
            <Button onClick={correct} disabled={busy || !text.trim() || text.trim() === m.text}>
              Save as v{m.version + 1}
            </Button>
            <Button variant="ghost" onClick={() => { setEditing(false); setText(m.text); }}>
              Cancel
            </Button>
          </div>
        </div>
      ) : (
        <p className={`text-sm leading-relaxed ${m.status === "forgotten" ? "line-through" : ""}`}>{m.text}</p>
      )}
      <div className="mt-2.5 flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <MemoryMeta m={m} />
          {inactive && <span className="text-xs font-medium text-muted">{m.status}</span>}
          {m.supersedes && <span className="text-xs text-muted">supersedes {m.supersedes}</span>}
        </div>
        {canEdit && !editing && (
          <div className="flex items-center gap-2">
            <label className="sr-only" htmlFor={`scope-${m.id}`}>Scope</label>
            <select
              id={`scope-${m.id}`}
              value={m.scope}
              disabled={busy}
              onChange={(e) => changeScope(e.target.value as MemoryScope)}
              className="rounded-md border border-line bg-surface px-2 py-1 text-xs"
            >
              <option value="successor">successor</option>
              <option value="team">team</option>
              <option value="never_transfer">never transfer</option>
            </select>
            <button onClick={() => setEditing(true)} className="text-xs font-medium text-accent hover:underline">Correct</button>
            {confirmForget ? (
              <span className="flex items-center gap-1.5 text-xs">
                <span className="text-danger">Forget for good?</span>
                <button onClick={forget} disabled={busy} className="font-medium text-danger hover:underline">Yes</button>
                <button onClick={() => setConfirmForget(false)} className="text-muted hover:underline">No</button>
              </span>
            ) : (
              <button onClick={() => setConfirmForget(true)} className="text-xs font-medium text-danger hover:underline">Forget</button>
            )}
          </div>
        )}
      </div>
      {error && <div className="mt-2"><ErrorNote message={error} /></div>}
    </li>
  );
}

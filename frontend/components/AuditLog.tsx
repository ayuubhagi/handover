"use client";

import { Button, Card, ErrorNote, Loading } from "./ui";
import { api } from "../lib/api";
import { useLive, useLoad } from "../lib/hooks";
import { personName } from "../lib/types";

export function AuditLog() {
  const audit = useLoad(() => api.audit(20));
  useLive(() => audit.reload());

  return (
    <div>
      <div className="mb-5 max-w-2xl">
        <h2 className="text-lg font-semibold">Audit</h2>
        <p className="mt-2 text-muted">Every read and governance action: who did it, which memories, whether it was allowed, and why.</p>
      </div>
      <Card title="Latest 20" aside={<Button variant="ghost" onClick={audit.reload}>Refresh</Button>}>
        {audit.error && <ErrorNote message={audit.error} onRetry={audit.reload} />}
        {audit.loading && !audit.data && <Loading label="Loading audit log" />}
        {audit.data?.length === 0 && <p className="text-sm text-muted">No entries yet. Ask a question or govern a memory.</p>}
        {audit.data && audit.data.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-xs uppercase tracking-wide text-muted">
                <tr className="border-b border-line">
                  <th className="py-2 pr-4 font-medium">Time</th>
                  <th className="py-2 pr-4 font-medium">Who</th>
                  <th className="py-2 pr-4 font-medium">Action</th>
                  <th className="py-2 pr-4 font-medium">Memories</th>
                  <th className="py-2 pr-4 font-medium">Result</th>
                  <th className="py-2 font-medium">Reason</th>
                </tr>
              </thead>
              <tbody>
                {audit.data.map((a, i) => (
                  <tr key={`${a.ts}-${i}`} className="border-b border-line/60 align-top last:border-0">
                    <td className="whitespace-nowrap py-2 pr-4 font-mono text-xs text-muted">{new Date(a.ts).toLocaleTimeString()}</td>
                    <td className="py-2 pr-4">{personName(a.actor_id)}</td>
                    <td className="py-2 pr-4">{a.action}</td>
                    <td className="py-2 pr-4 font-mono text-xs">{a.memory_ids.join(", ") || "none"}</td>
                    <td className="py-2 pr-4">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${a.allowed ? "bg-accent-soft text-accent" : "bg-danger-soft text-danger"}`}>
                        {a.allowed ? "allowed" : "blocked"}
                      </span>
                    </td>
                    <td className="py-2 text-muted">{a.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}

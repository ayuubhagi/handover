// In-browser mock of the TEAM.md API contract. Fictional bank-ops data only.
// Same shapes as the real backend, so screens can be built and rehearsed before the routes exist.
// Everything here is shown under a "Mock data" badge in the header.

import { getUserId } from "./session";
import type {
  AuditEntry,
  Gap,
  HandoverApi,
  LiveEvent,
  Memory,
  MemoryScope,
  RunbookStep,
} from "./types";

class MockError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(`${status}: ${message}`);
  }
}

const EXPIRES = "2027-01-31T00:00:00Z";
const now = () => new Date().toISOString();
const wait = (ms = 350) => new Promise((r) => setTimeout(r, ms + Math.random() * 200));
const clone = <T>(v: T): T => JSON.parse(JSON.stringify(v));

let seq = 100;
const nextId = (prefix: string) => `${prefix}_${++seq}`;

function mem(
  id: string,
  kind: Memory["kind"],
  text: string,
  scope: MemoryScope,
  clip: string,
  session: string,
  extra: Partial<Memory> = {},
): Memory {
  return {
    id,
    owner_id: "u_expert",
    kind,
    text,
    scope,
    status: "active",
    version: 1,
    supersedes: null,
    derived_from: [],
    source_clip_id: clip,
    session_id: session,
    created_at: "2026-11-14T12:00:00Z",
    expires_at: EXPIRES,
    ...extra,
  };
}

interface State {
  memories: Memory[];
  clips: Record<string, string>;
  runbook: RunbookStep[];
  gaps: (Gap & { owner_id: string })[];
  audit: (AuditEntry & { id: string })[];
  sessions: Record<string, number>;
}

function seed(): State {
  return {
    clips: {
      c_1: "When the overnight payments batch stalls, restart the payments queue before you touch the ledger database. If you restart the database first, the batch reloads and every payment in it posts twice. Then you spend the whole morning reversing them.",
      c_2: "When a payment gets held by sanctions screening and compliance tells you to push it through by hand, you re-key it on the LoanDesk backup screen. Almost nobody uses that screen, so nobody remembers this: the amount field comes pre-filled with zeros. Delete them before you type the amount. The approvers will look right past it, because the screen looks completely normal.",
      c_3: "Halvorsen Freight is our touchiest client. Their treasurer, Ingrid, has a standing verbal agreement that we release their Friday wires up to two million without the second approver. That is not written down anywhere.",
      c_4: "Never reuse routing flag R7 for anything new. It used to switch on the old auto-release router. That code is dead everywhere except PAY-08, which nobody has switched off yet. If R7 gets turned on and PAY-08 picks up the job, it starts releasing payments on its own. PAY-08 is supposed to be decommissioned at the end of the month.",
      c_5: "The reconciliation report from LedgerOne is always wrong on the first business day of the month, because of a timezone bug. Rerun it after ten a.m. Eastern and it comes out right.",
      c_6: "For a stalled batch, actually, the first thing I do is check the ledger database locks, clear them, and only then worry about the queue.",
      c_7: "On-call escalation goes to the payments ops duty manager first, then to the LedgerOne vendor hotline if it's still down after thirty minutes. The hotline is useless before then.",
    },
    memories: [
      mem("m_1", "procedure", "When the overnight payments batch stalls, restart the payments queue before touching the ledger database. Restarting the database first reloads the batch and every payment posts twice.", "successor", "c_1", "s_1"),
      mem("m_2", "procedure", "To push through a payment held by sanctions screening, re-key it on the LoanDesk backup screen. The amount field there comes pre-filled with zeros: delete them before typing the amount.", "successor", "c_2", "s_1"),
      mem("m_3", "workaround", "Approvers routinely miss the pre-filled zeros on the LoanDesk backup screen because the screen looks normal. Do not rely on the approvers to catch it.", "successor", "c_2", "s_1"),
      mem("m_4", "client", "Halvorsen Freight has a verbal agreement with treasurer Ingrid: Friday wires up to 2 million are released without the second approver. It is not documented anywhere.", "never_transfer", "c_3", "s_1"),
      mem("m_5", "system", "Never reuse routing flag R7. It used to enable the old auto-release router, and that code still runs on PAY-08. If R7 is turned on and PAY-08 picks up the job, it releases payments on its own. PAY-08 is decommissioned at the end of the month.", "team", "c_4", "s_1", { expires_at: "2026-12-05T12:00:00Z" }),
      mem("m_6", "workaround", "The LedgerOne reconciliation report is wrong on the first business day of each month because of a timezone bug. Rerun it after 10 a.m. Eastern.", "team", "c_5", "s_1"),
      mem("m_7", "procedure", "For a stalled payments batch, first check and clear the ledger database locks, then deal with the queue.", "successor", "c_6", "s_1"),
      mem("m_8", "procedure", "On-call escalation: payments ops duty manager first, then the LedgerOne vendor hotline if the outage lasts more than 30 minutes.", "team", "c_7", "s_1"),
      mem("m_9", "procedure", "Backup screen checklist: delete the pre-filled zeros in the amount field, type the amount, and check it yourself before approval. The approvers will not catch it.", "successor", "c_2", "s_1", { derived_from: ["m_2", "m_3"] }),
    ],
    runbook: [
      { id: "r_1", text: "Stalled overnight batch: restart the payments queue before touching the ledger database.", derived_from: ["m_1"], status: "active" },
      { id: "r_2", text: "Re-keying a held payment on the LoanDesk backup screen: delete the pre-filled zeros in the amount field and check the amount yourself before approval.", derived_from: ["m_9"], status: "active" },
      { id: "r_3", text: "First business day of the month: rerun the LedgerOne reconciliation report after 10 a.m. Eastern.", derived_from: ["m_6"], status: "active" },
      { id: "r_4", text: "Routing flags: never reuse R7 while PAY-08 is still running.", derived_from: ["m_5"], status: "active" },
      { id: "r_5", text: "Outage over 30 minutes: escalate to the duty manager, then the LedgerOne vendor hotline.", derived_from: ["m_8"], status: "active" },
      { id: "r_6", text: "Friday wires for Halvorsen Freight: follow the release arrangement agreed with their treasurer.", derived_from: ["m_4"], status: "active" },
    ],
    gaps: [
      { id: "g_1", owner_id: "u_expert", question: "You told me to restart the payments queue before touching the ledger database, but you also said you clear the database locks first. Which one comes first when the batch stalls?", kind: "contradiction", from_memory_ids: ["m_1", "m_7"], status: "open" },
      { id: "g_2", owner_id: "u_expert", question: "You said the backup screen pre-fills the amount field with zeros. Is there any way to catch a wrong amount before the payment actually posts?", kind: "missing", from_memory_ids: ["m_2"], status: "open" },
    ],
    audit: [],
    sessions: {},
  };
}

let db: State = seed();

// ---------- live events (stands in for WS /live) ----------
type Listener = (e: LiveEvent) => void;
const listeners = new Set<Listener>();
function emit(e: LiveEvent) {
  setTimeout(() => listeners.forEach((l) => l(clone(e))), 150);
}

// ---------- access rules (mirror the scope rules in PLAN.md) ----------
function canRead(viewer: string, m: Memory): boolean {
  if (m.owner_id === viewer) return true;
  if (m.status !== "active") return false;
  if (m.expires_at && new Date(m.expires_at).getTime() <= Date.now()) return false;
  if (viewer === "u_successor") return m.scope === "successor" || m.scope === "team";
  if (viewer === "u_outsider") return m.scope === "team";
  return false;
}

function logAudit(entry: Omit<AuditEntry, "ts">): string {
  const id = nextId("a");
  db.audit.unshift({ ...entry, id, ts: now() });
  return id;
}

function getOwned(id: string): Memory {
  const m = db.memories.find((x) => x.id === id);
  if (!m) throw new MockError("memory not found", 404);
  const viewer = getUserId();
  if (m.owner_id !== viewer) {
    logAudit({ actor_id: viewer, action: "govern", memory_ids: [id], allowed: false, reason: "only the owner can change a memory" });
    throw new MockError("only the owner can change this memory", 403);
  }
  return m;
}

function visibleRunbook(viewer: string): RunbookStep[] {
  return db.runbook.filter(
    (s) =>
      s.status === "active" &&
      s.derived_from.every((id) => {
        const m = db.memories.find((x) => x.id === id);
        return m && m.status === "active" && canRead(viewer, m);
      }),
  );
}

// ---------- scripted interview ----------
interface Turn {
  question: string;
  transcript: string;
  memory?: { kind: Memory["kind"]; text: string; scope: MemoryScope };
  gap?: { kind: Gap["kind"]; question: string };
  answersGap?: string;
}

const SCRIPT: Turn[] = [
  {
    question: "You told me to restart the payments queue before touching the ledger database, but you also said you clear the database locks first. Which one comes first when the batch stalls?",
    transcript: "Good catch. Clear the database locks first, but never restart the database. Clearing locks is safe. Restarting the database is what reloads the batch and causes the duplicates. So: clear the locks, then restart the queue.",
    memory: { kind: "procedure", text: "Stalled payments batch: clear the ledger database locks first, then restart the payments queue. Never restart the ledger database; that reloads the batch and every payment posts twice.", scope: "successor" },
    answersGap: "g_1",
  },
  {
    question: "You said the backup screen pre-fills the amount field with zeros. Is there any way to catch a wrong amount before the payment actually posts?",
    transcript: "Yes. Before you release it, open the payment in the LoanDesk pending queue and compare the amount with compliance's original instruction. The pending queue shows the real figure. If they don't match, cancel it there and re-key it.",
    memory: { kind: "procedure", text: "Before releasing a payment re-keyed on the LoanDesk backup screen, open it in the LoanDesk pending queue and compare the amount with compliance's original instruction; if it differs, cancel and re-key.", scope: "successor" },
    gap: { kind: "missing", question: "Who do you tell when a re-keyed payment had the wrong amount and you cancelled it?" },
    answersGap: "g_2",
  },
  {
    question: "Who do you tell when a re-keyed payment had the wrong amount and you cancelled it?",
    transcript: "Email the compliance analyst who approved the override and copy the payments ops duty manager. Put the payment reference in, so the re-key doesn't get flagged as a second release.",
    memory: { kind: "procedure", text: "After cancelling a wrong re-keyed payment, email the approving compliance analyst, copy the payments ops duty manager, and include the payment reference.", scope: "team" },
  },
  {
    question: "Is there anything about month-end, other than the LedgerOne reconciliation report, that your successor should know?",
    transcript: "That's the main one. The rest of month-end runs itself once the report is right.",
  },
];

// ---------- simple keyword relevance (mock only) ----------
const STOP = new Set(["the", "a", "an", "to", "do", "i", "what", "how", "is", "of", "and", "or", "if", "when", "should", "before", "after", "on", "in", "it", "for", "my", "we", "you"]);
const words = (s: string) =>
  s.toLowerCase().replace(/[^a-z0-9 ]/g, " ").split(/\s+/).filter((w) => w.length > 2 && !STOP.has(w));

function relevant(question: string): Memory[] {
  const q = new Set(words(question));
  return db.memories
    .filter((m) => m.status === "active")
    .map((m) => ({ m, score: words(m.text).filter((w) => q.has(w)).length }))
    .filter((x) => x.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, 4)
    .map((x) => x.m);
}

// ---------- the API ----------
export const mockApi: HandoverApi = {
  async startSession(expertId) {
    await wait();
    const session_id = nextId("s");
    db.sessions[session_id] = 0;
    logAudit({ actor_id: getUserId(), action: "start_session", memory_ids: [], allowed: true, reason: `interview with ${expertId}` });
    return { session_id, first_question_text: SCRIPT[0].question, first_question_audio_url: null };
  },

  async answer(sessionId, _audio, transcript) {
    await wait(900);
    const turn = db.sessions[sessionId];
    if (turn === undefined) throw new MockError("session not found", 404);
    const t = SCRIPT[Math.min(turn, SCRIPT.length - 1)];
    db.sessions[sessionId] = turn + 1;
    const clipId = nextId("c");
    db.clips[clipId] = transcript?.trim() || t.transcript;
    const memories_created: Memory[] = [];
    const gaps_created: Gap[] = [];
    if (t.memory) {
      const m = mem(nextId("m"), t.memory.kind, t.memory.text, t.memory.scope, clipId, sessionId, {
        created_at: now(),
        derived_from: t.answersGap ? db.gaps.find((g) => g.id === t.answersGap)?.from_memory_ids ?? [] : [],
      });
      db.memories.push(m);
      memories_created.push(clone(m));
      emit({ type: "memory_changed", memory: m });
    }
    if (t.answersGap) {
      const g = db.gaps.find((x) => x.id === t.answersGap);
      if (g) g.status = "answered";
    }
    if (t.gap) {
      const g = { id: nextId("g"), owner_id: "u_expert", question: t.gap.question, kind: t.gap.kind, from_memory_ids: memories_created.map((m) => m.id), status: "open" as const };
      db.gaps.push(g);
      const { owner_id: _o, ...out } = g;
      void _o;
      gaps_created.push(out);
    }
    const next = SCRIPT[turn + 1];
    return {
      transcript: db.clips[clipId],
      memories_created,
      gaps_created,
      next_question_text: next ? next.question : "That covers everything I had for today. Thank you.",
      next_question_audio_url: null,
      used_memory_ids: t.answersGap ? db.gaps.find((g) => g.id === t.answersGap)?.from_memory_ids ?? [] : [],
    };
  },

  async listMemories(ownerId) {
    await wait();
    const viewer = getUserId();
    return clone(db.memories.filter((m) => m.owner_id === ownerId && canRead(viewer, m)));
  },

  async setScope(id, scope) {
    await wait();
    const m = getOwned(id);
    const before = m.scope;
    m.scope = scope;
    logAudit({ actor_id: getUserId(), action: "set_scope", memory_ids: [id], allowed: true, reason: `${before} -> ${scope}` });
    emit({ type: "memory_changed", memory: m });
    emit({ type: "runbook_changed" });
    return clone(m);
  },

  async correct(id, text) {
    await wait();
    const old = getOwned(id);
    if (old.status !== "active") throw new MockError("only active memories can be corrected", 409);
    old.status = "corrected";
    const fresh: Memory = { ...clone(old), id: nextId("m"), text, status: "active", version: old.version + 1, supersedes: old.id, created_at: now() };
    db.memories.push(fresh);
    for (const s of db.runbook) {
      if (s.derived_from.includes(old.id)) s.derived_from = s.derived_from.map((d) => (d === old.id ? fresh.id : d));
    }
    logAudit({ actor_id: getUserId(), action: "correct", memory_ids: [old.id, fresh.id], allowed: true, reason: `v${old.version} superseded by v${fresh.version}` });
    emit({ type: "memory_changed", memory: old });
    emit({ type: "memory_changed", memory: fresh });
    emit({ type: "runbook_changed" });
    return { old: clone(old), new: clone(fresh) };
  },

  async forget(id) {
    await wait();
    const root = getOwned(id);
    // Cascade: the memory plus every memory derived from it, transitively.
    const forgotten = new Set<string>([root.id]);
    let grew = true;
    while (grew) {
      grew = false;
      for (const m of db.memories) {
        if (!forgotten.has(m.id) && m.status === "active" && m.derived_from.some((d) => forgotten.has(d))) {
          forgotten.add(m.id);
          grew = true;
        }
      }
    }
    for (const m of db.memories) if (forgotten.has(m.id)) m.status = "forgotten";
    const removed: string[] = [];
    for (const s of db.runbook) {
      if (s.status === "active" && s.derived_from.some((d) => forgotten.has(d))) {
        s.status = "removed";
        removed.push(s.id);
      }
    }
    // Same as the backend: gaps that quote a forgotten memory are deleted.
    db.gaps = db.gaps.filter((g) => !g.from_memory_ids.some((m) => forgotten.has(m)));
    const audit_id = logAudit({ actor_id: getUserId(), action: "forget", memory_ids: [...forgotten], allowed: true, reason: `forgotten by owner; ${removed.length} runbook step(s) removed` });
    for (const m of db.memories) if (forgotten.has(m.id)) emit({ type: "memory_changed", memory: m });
    emit({ type: "runbook_changed" });
    return { forgotten_ids: [...forgotten], runbook_steps_removed: removed, audit_id };
  },

  async ask(question, memory) {
    await wait(700);
    const viewer = getUserId();
    if (!memory) {
      const audit_id = logAudit({ actor_id: viewer, action: "ask", memory_ids: [], allowed: true, reason: "memory off: no memories read" });
      return {
        answer_text: "I don't have any team-specific knowledge to draw on. In general, check your internal runbooks and ask the system owner before restarting production services.",
        sources: [],
        blocked_count: 0,
        audit_id,
      };
    }
    const hits = relevant(question);
    const allowed = hits.filter((m) => canRead(viewer, m));
    const blocked = hits.filter((m) => !canRead(viewer, m));
    for (const m of blocked) {
      logAudit({ actor_id: viewer, action: "read", memory_ids: [m.id], allowed: false, reason: `scope ${m.scope} not readable by ${viewer}` });
    }
    const audit_id = logAudit({ actor_id: viewer, action: "ask", memory_ids: allowed.map((m) => m.id), allowed: true, reason: `${allowed.length} memories in scope, ${blocked.length} blocked` });
    const answer_text = allowed.length
      ? `From what was handed over: ${allowed.map((m) => m.text).join(" ")}`
      : blocked.length
        ? "I can't share anything on that with you. The relevant knowledge isn't in your scope."
        : "That hasn't been covered yet. It's been added as a gap for the next session.";
    return {
      answer_text,
      sources: allowed.map((m) => ({ memory: clone(m), clip_url: null, transcript: db.clips[m.source_clip_id] ?? "" })),
      blocked_count: blocked.length,
      audit_id,
    };
  },

  async runbook() {
    await wait(200);
    return clone(visibleRunbook(getUserId()));
  },

  async audit(limit = 20) {
    await wait(200);
    return clone(db.audit.slice(0, limit)).map(({ id: _id, ...rest }) => {
      void _id;
      return rest;
    });
  },

  async gaps(ownerId) {
    await wait(200);
    return db.gaps
      .filter((g) => g.owner_id === ownerId)
      .map(({ owner_id: _o, ...g }) => {
        void _o;
        return clone(g);
      });
  },

  subscribe(onEvent, onStatus) {
    listeners.add(onEvent);
    setTimeout(() => onStatus?.(true), 0);
    return () => {
      listeners.delete(onEvent);
    };
  },

  mediaUrl(url) {
    return url;
  },
};

/** Reset mock data to the seed (used by the "Reset demo data" control in mock mode). */
export function resetMock() {
  db = seed();
  emit({ type: "runbook_changed" });
}

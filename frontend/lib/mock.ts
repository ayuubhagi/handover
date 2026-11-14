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
      c_1: "When SWIFT messages get stuck, restart the queue listener first. Do not re-send the MT103s until the listener is back, or you get duplicates.",
      c_2: "The payments queue, you restart that before you touch the database. Every time.",
      c_3: "Northwind Freight sends their batch file with a trailing blank line. The importer chokes on it, so I strip it by hand before the six a.m. run.",
      c_4: "RECON-02 is the old reconciliation box. It's being retired at year end, so don't build anything new on it.",
      c_5: "Between us: if the queue is down more than two hours, I call Priya in treasury directly. That's a personal arrangement.",
      c_6: "After the maintenance window, that's when you restart the payments queue. Database first, then the queue.",
    },
    memories: [
      mem("m_1", "procedure", "When SWIFT messages are stuck, restart the SWIFT queue listener first; only re-send MT103s once it is back, to avoid duplicates.", "successor", "c_1", "s_1"),
      mem("m_2", "procedure", "Restart the payments queue before touching the database.", "team", "c_2", "s_1"),
      mem("m_3", "workaround", "Northwind Freight's batch file has a trailing blank line; strip it manually before the 6:00 import or the importer fails.", "successor", "c_3", "s_1"),
      mem("m_4", "system", "RECON-02 (old reconciliation server) is retired at year end; build nothing new on it.", "team", "c_4", "s_1", { expires_at: "2026-12-31T00:00:00Z" }),
      mem("m_5", "client", "If the payments queue is down for more than two hours, Dana escalates directly to Priya in treasury.", "never_transfer", "c_5", "s_1"),
      mem("m_6", "procedure", "After the database maintenance window, restart the payments queue (database first, then queue).", "successor", "c_6", "s_2"),
    ],
    runbook: [
      { id: "r_1", text: "Stuck SWIFT messages: restart the SWIFT queue listener, confirm it is up, then re-send pending MT103s.", derived_from: ["m_1"], status: "active" },
      { id: "r_2", text: "Before any database work: restart the payments queue.", derived_from: ["m_2"], status: "active" },
      { id: "r_3", text: "05:45 daily: open the Northwind Freight batch file and remove the trailing blank line.", derived_from: ["m_3"], status: "active" },
      { id: "r_4", text: "Morning check: confirm SWIFT and payments queues are drained before opening the 06:00 import.", derived_from: ["m_1", "m_2"], status: "active" },
      { id: "r_5", text: "Do not schedule new reconciliation jobs on RECON-02.", derived_from: ["m_4"], status: "active" },
    ],
    gaps: [
      { id: "g_1", owner_id: "u_expert", question: "In session 1 you said to restart the payments queue before touching the database, but in session 2 you said database first, then the queue. Which order is right?", kind: "contradiction", from_memory_ids: ["m_2", "m_6"], status: "open" },
      { id: "g_2", owner_id: "u_expert", question: "What should Sam do if the SWIFT queue listener does not come back after a restart?", kind: "missing", from_memory_ids: ["m_1"], status: "open" },
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
    question: "Last time you gave two different orders for restarting the payments queue and the database. Which one is right?",
    transcript: "Good catch. Database maintenance first, then restart the payments queue. The other way round was the old system.",
    memory: { kind: "procedure", text: "Correct order: finish database maintenance first, then restart the payments queue (the reverse order applied to the old system).", scope: "successor" },
    answersGap: "g_1",
  },
  {
    question: "What should Sam do if the SWIFT queue listener does not come back after a restart?",
    transcript: "Check the disk on the SWIFT gateway. Nine times out of ten it's the log volume filling up. Clear old logs and restart again.",
    memory: { kind: "system", text: "If the SWIFT listener won't restart, check the gateway's log volume; clear old logs and restart.", scope: "successor" },
    gap: { kind: "missing", question: "Which log files on the SWIFT gateway are safe to delete?" },
    answersGap: "g_2",
  },
  {
    question: "Which log files on the SWIFT gateway are safe to delete?",
    transcript: "Anything in the archive folder older than thirty days. Never touch the current day's journal.",
    memory: { kind: "procedure", text: "On the SWIFT gateway, delete archive logs older than 30 days only; never delete the current day's journal.", scope: "successor" },
  },
  {
    question: "Is there anything about client files, other than Northwind Freight, that Sam should know?",
    transcript: "That's the main one. Everything else comes through clean.",
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

  async answer(sessionId) {
    await wait(900);
    const turn = db.sessions[sessionId];
    if (turn === undefined) throw new MockError("session not found", 404);
    const t = SCRIPT[Math.min(turn, SCRIPT.length - 1)];
    db.sessions[sessionId] = turn + 1;
    const clipId = nextId("c");
    db.clips[clipId] = t.transcript;
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
      transcript: t.transcript,
      memories_created,
      gaps_created,
      next_question_text: next ? next.question : "That covers everything I had for today. Thank you, Dana.",
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
      ? `Based on what Dana recorded: ${allowed.map((m) => m.text).join(" ")}`
      : blocked.length
        ? "I can't share anything on that with you. The relevant knowledge isn't in your scope."
        : "Dana hasn't covered that yet. I'll add it as a gap for her next session.";
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

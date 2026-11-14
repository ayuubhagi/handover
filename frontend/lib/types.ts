// Mirrors the fixed API contract in TEAM.md. Do not change shapes here without updating TEAM.md first.

export type UserId = "u_expert" | "u_successor" | "u_outsider";
export type MemoryKind = "procedure" | "system" | "client" | "workaround";
export type MemoryScope = "successor" | "team" | "never_transfer";
export type MemoryStatus = "active" | "corrected" | "forgotten";

export interface Memory {
  id: string;
  owner_id: string;
  kind: MemoryKind;
  text: string;
  scope: MemoryScope;
  status: MemoryStatus;
  version: number;
  supersedes: string | null;
  derived_from: string[];
  source_clip_id: string;
  session_id: string;
  created_at: string;
  expires_at: string;
}

export type GapKind = "missing" | "contradiction";
export type GapStatus = "open" | "asked" | "answered";

export interface Gap {
  id: string;
  question: string;
  kind: GapKind;
  from_memory_ids: string[];
  status: GapStatus;
}

export interface StartSessionResponse {
  session_id: string;
  first_question_text: string;
  first_question_audio_url: string | null;
}

export interface AnswerResponse {
  transcript: string;
  memories_created: Memory[];
  gaps_created: Gap[];
  next_question_text: string;
  next_question_audio_url: string | null;
  used_memory_ids: string[];
}

export interface CorrectResponse {
  old: Memory;
  new: Memory;
}

export interface ForgetResponse {
  forgotten_ids: string[];
  runbook_steps_removed: string[];
  audit_id: string;
}

export interface AskSource {
  memory: Memory;
  clip_url: string | null;
  transcript: string | null;
}

export interface AskResponse {
  answer_text: string;
  sources: AskSource[];
  blocked_count: number;
  audit_id: string;
}

export interface RunbookStep {
  id: string;
  text: string;
  derived_from: string[];
  /** active | needs_review (a source memory was corrected); removed steps are not returned. */
  status: string;
}

export interface AuditEntry {
  actor_id: string;
  action: string;
  memory_ids: string[];
  allowed: boolean;
  reason: string;
  ts: string;
}

export type LiveEvent =
  | { type: "memory_changed"; memory: Memory }
  | { type: "runbook_changed" };

export interface HandoverApi {
  startSession(expertId: string): Promise<StartSessionResponse>;
  /** Send a recorded answer, or a typed transcript (backend extension: `transcript` form field, used when there is no speech-to-text key). */
  answer(sessionId: string, audio: Blob | null, transcript?: string): Promise<AnswerResponse>;
  listMemories(ownerId: string): Promise<Memory[]>;
  setScope(id: string, scope: MemoryScope): Promise<Memory>;
  correct(id: string, text: string): Promise<CorrectResponse>;
  forget(id: string): Promise<ForgetResponse>;
  ask(question: string, memory: boolean): Promise<AskResponse>;
  runbook(): Promise<RunbookStep[]>;
  audit(limit?: number): Promise<AuditEntry[]>;
  gaps(ownerId: string): Promise<Gap[]>;
  /** Subscribe to WS /live. Returns an unsubscribe function. */
  subscribe(onEvent: (e: LiveEvent) => void, onStatus?: (connected: boolean) => void): () => void;
  /** Turn a clip/audio URL from the API into something an <audio> tag can play. */
  mediaUrl(url: string | null): string | null;
}

export const PEOPLE: { id: UserId; name: string; role: string }[] = [
  { id: "u_expert", name: "Handing over", role: "Recording what you know" },
  { id: "u_successor", name: "Taking over", role: "Asking what was handed over" },
  { id: "u_outsider", name: "Other team", role: "Sees only what is shared with the team" },
];

export function personName(id: string): string {
  return PEOPLE.find((p) => p.id === id)?.name ?? id;
}

import { API_URL, USE_MOCKS } from "./config";
import { mockApi } from "./mock";
import { getUserId } from "./session";
import type {
  AnswerResponse,
  AskResponse,
  AuditEntry,
  CorrectResponse,
  ForgetResponse,
  Gap,
  HandoverApi,
  LiveEvent,
  Memory,
  RunbookStep,
  StartSessionResponse,
} from "./types";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number | null,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("X-User-Id", getUserId());
  if (typeof init.body === "string") headers.set("Content-Type", "application/json");
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(
      `Can't reach the backend at ${API_URL}. Start it, or set NEXT_PUBLIC_USE_MOCKS=true to use demo data.`,
      null,
    );
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body?.detail === "string" ? body.detail : JSON.stringify(body?.detail ?? body);
    } catch {}
    throw new ApiError(`${res.status}: ${detail}`, res.status);
  }
  return res.json() as Promise<T>;
}

const json = (body: unknown) => JSON.stringify(body);
const enc = encodeURIComponent;

export const realApi: HandoverApi = {
  startSession: (expertId) =>
    request<StartSessionResponse>("/sessions", { method: "POST", body: json({ expert_id: expertId }) }),

  answer: (sessionId, audio, transcript) => {
    const form = new FormData();
    if (audio) {
      const ext = audio.type.includes("ogg") ? "ogg" : audio.type.includes("mp4") ? "m4a" : "webm";
      form.append("audio", audio, `answer.${ext}`);
    }
    if (transcript?.trim()) form.append("transcript", transcript.trim());
    return request<AnswerResponse>(`/sessions/${enc(sessionId)}/answer`, { method: "POST", body: form });
  },

  listMemories: (ownerId) => request<Memory[]>(`/memories?owner_id=${enc(ownerId)}`),

  setScope: (id, scope) =>
    request<Memory>(`/memories/${enc(id)}/scope`, { method: "PATCH", body: json({ scope }) }),

  correct: (id, text) =>
    request<CorrectResponse>(`/memories/${enc(id)}/correct`, { method: "POST", body: json({ text }) }),

  forget: (id) => request<ForgetResponse>(`/memories/${enc(id)}/forget`, { method: "POST" }),

  ask: (question, memory) => request<AskResponse>("/ask", { method: "POST", body: json({ question, memory }) }),

  runbook: () => request<RunbookStep[]>("/runbook"),

  audit: (limit = 20) => request<AuditEntry[]>(`/audit?limit=${limit}`),

  gaps: (ownerId) => request<Gap[]>(`/gaps?owner_id=${enc(ownerId)}`),

  subscribe(onEvent: (e: LiveEvent) => void, onStatus?: (c: boolean) => void) {
    let ws: WebSocket | null = null;
    let closed = false;
    let retry = 0;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const wsBase = API_URL.replace(/^http/, "ws");
    const connect = () => {
      if (closed) return;
      // Browsers can't set headers on a WebSocket, so the backend accepts ?user_id= for /live.
      ws = new WebSocket(`${wsBase}/live?user_id=${enc(getUserId())}`);
      ws.onopen = () => {
        retry = 0;
        onStatus?.(true);
      };
      ws.onmessage = (msg) => {
        try {
          onEvent(JSON.parse(msg.data) as LiveEvent);
        } catch {}
      };
      ws.onclose = () => {
        onStatus?.(false);
        if (closed) return;
        timer = setTimeout(connect, Math.min(10000, 500 * 2 ** retry++));
      };
      ws.onerror = () => ws?.close();
    };
    connect();
    return () => {
      closed = true;
      clearTimeout(timer);
      ws?.close();
    };
  },

  mediaUrl(url) {
    if (!url) return null;
    const abs = /^https?:\/\//.test(url) ? url : `${API_URL}${url.startsWith("/") ? "" : "/"}${url}`;
    if (abs.includes("user_id=")) return abs;
    // <audio> can't send X-User-Id, so pass the viewer as a query param (backend fallback for /clips).
    return `${abs}${abs.includes("?") ? "&" : "?"}user_id=${enc(getUserId())}`;
  },
};

export const api: HandoverApi = USE_MOCKS ? mockApi : realApi;

export function errorMessage(e: unknown): string {
  return e instanceof Error ? e.message : String(e);
}

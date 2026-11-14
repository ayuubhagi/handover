import { API_URL, USE_MOCKS } from "./config";
import { mockApi } from "./mock";
import { cachedToken, clearToken, getToken } from "./auth";
import { getUserId } from "./session";
import { dlog } from "./debuglog";
import type {
  UserId,
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

async function send(path: string, init: RequestInit, user: UserId): Promise<Response> {
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${await getToken(user)}`);
  if (typeof init.body === "string") headers.set("Content-Type", "application/json");
  return fetch(`${API_URL}${path}`, { ...init, headers });
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = init.method ?? "GET";
  const t0 = performance.now();
  const ms = () => Math.round(performance.now() - t0);
  try {
    const out = await requestInner<T>(path, init);
    dlog("info", "api", `${method} ${path} ok`, { ms: ms(), user: getUserId() });
    return out;
  } catch (e) {
    const err = e as ApiError;
    dlog("error", "api", `${method} ${path} failed: ${err.message}`, { ms: ms(), status: err.status ?? null, user: getUserId() });
    throw e;
  }
}

async function requestInner<T>(path: string, init: RequestInit = {}): Promise<T> {
  const user = getUserId();
  try {
    await getToken(user);
  } catch (e) {
    throw new ApiError(e instanceof Error ? e.message : String(e), 401);
  }
  let res: Response;
  try {
    res = await send(path, init, user);
    if (res.status === 401) {
      // Token expired or the backend restarted with a new secret: log in again and retry once.
      clearToken(user);
      res = await send(path, init, user);
    }
  } catch {
    throw new ApiError(
      `Can't reach the backend at ${API_URL}, or it crashed (an unhandled 500 has no CORS headers, so the browser hides it; check the backend log, e.g. MONGODB_URI not set). Start it, or set NEXT_PUBLIC_USE_MOCKS=true to use demo data.`,
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
    const retryLater = () => {
      if (!closed) timer = setTimeout(connect, Math.min(10000, 500 * 2 ** retry++));
    };
    const connect = async () => {
      if (closed) return;
      let token: string;
      try {
        token = await getToken();
      } catch (e) {
        dlog("error", "ws", `live login failed: ${String(e)}`);
        onStatus?.(false);
        return retryLater();
      }
      if (closed) return;
      // Browsers can't set headers on a WebSocket, so the backend reads ?token= for /live.
      ws = new WebSocket(`${wsBase}/live?token=${enc(token)}`);
      ws.onopen = () => {
        dlog("info", "ws", "live connected");
        retry = 0;
        onStatus?.(true);
      };
      ws.onmessage = (msg) => {
        try {
          onEvent(JSON.parse(msg.data) as LiveEvent);
        } catch (e) {
          dlog("warn", "ws", "bad live message", { data: String(msg.data).slice(0, 500), error: String(e) });
        }
      };
      ws.onclose = (ev) => {
        if (!closed) dlog("warn", "ws", `live closed code=${ev.code} reason=${ev.reason || "-"}`, { retry });
        onStatus?.(false);
        if (ev.code === 4401) clearToken();
        retryLater();
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
    let u: URL;
    try {
      u = new URL(url, `${API_URL}/`);
    } catch {
      return null;
    }
    // Never hand the bearer token to any host other than the backend.
    if (u.origin !== new URL(API_URL).origin || u.searchParams.has("token")) return u.toString();
    // <audio> can't send headers, so the backend reads ?token= for /clips. Data that contains clip
    // URLs comes from request(), which has already logged in, so the token is cached by now.
    const token = cachedToken();
    if (token) u.searchParams.set("token", token);
    return u.toString();
  },
};

export const api: HandoverApi = USE_MOCKS ? mockApi : realApi;

export function errorMessage(e: unknown): string {
  return e instanceof Error ? e.message : String(e);
}

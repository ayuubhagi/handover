import { API_URL, DEMO_MODE } from "./config";
import { getUserId } from "./session";
import type { UserId } from "./types";

// Local demo passcodes, "u_expert:code,u_successor:code,..." (NEXT_PUBLIC_DEMO_PASSCODES in .env.local).
// Unused on a public demo (NEXT_PUBLIC_DEMO_MODE=true), which logs in through POST /demo/login instead.
const PASSCODES: Record<string, string> = Object.fromEntries(
  (process.env.NEXT_PUBLIC_DEMO_PASSCODES || "")
    .split(",")
    .map((p) => p.trim().split(":"))
    .filter((p) => p.length >= 2)
    .map(([id, ...rest]) => [id, rest.join(":")]),
);

type Cached = { token: string; exp: number };
const tokens = new Map<UserId, Cached>();
const pending = new Map<UserId, Promise<string>>();

const valid = (c?: Cached) => !!c && c.exp * 1000 > Date.now() + 30_000;

/** Last token issued for the current viewer, if still valid. Sync, for <audio src>. */
export function cachedToken(user: UserId = getUserId()): string | null {
  const c = tokens.get(user);
  return valid(c) ? c!.token : null;
}

export function clearToken(user: UserId = getUserId()) {
  tokens.delete(user);
}

/** Token for the viewer, logging in silently via POST /login if needed. */
export function getToken(user: UserId = getUserId()): Promise<string> {
  const c = tokens.get(user);
  if (valid(c)) return Promise.resolve(c!.token);
  const inFlight = pending.get(user);
  if (inFlight) return inFlight;
  const p = (async () => {
    let res: Response;
    try {
      res = await fetch(`${API_URL}${DEMO_MODE ? "/demo/login" : "/login"}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(DEMO_MODE ? { user_id: user } : { user_id: user, passcode: PASSCODES[user] ?? "" }),
      });
    } catch {
      throw new Error(`Can't reach the backend at ${API_URL} to log in. Is it running?`);
    }
    if (!res.ok) {
      let detail = res.statusText;
      try {
        detail = (await res.json())?.detail ?? detail;
      } catch {}
      throw new Error(`Login as ${user} failed (${res.status}: ${detail}). ${DEMO_MODE ? "Is DEMO_MODE=true on the backend?" : "Check NEXT_PUBLIC_DEMO_PASSCODES in frontend/.env.local."}`);
    }
    const body = (await res.json()) as { token: string; expires_at: number };
    tokens.set(user, { token: body.token, exp: body.expires_at });
    return body.token;
  })().finally(() => pending.delete(user));
  pending.set(user, p);
  return p;
}

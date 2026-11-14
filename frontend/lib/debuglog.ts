// Debug log capture for demo testing. Everything goes to frontend/logs/client.jsonl via /api/logs,
// so a teammate (or their AI assistant) can read what happened. Tokens are scrubbed before sending.

type Level = "info" | "warn" | "error";
type Entry = { ts: string; level: Level; kind: string; msg: string; data?: unknown; page?: string };

const queue: Entry[] = [];
let timer: ReturnType<typeof setTimeout> | undefined;
let installed = false;

const scrub = (s: string) =>
  s.replace(/([?&]token=)[^&\s"']+/g, "$1[redacted]").replace(/(Bearer\s+)[\w.\-]+/g, "$1[redacted]");

function toText(v: unknown): string {
  if (v instanceof Error) return `${v.name}: ${v.message}${v.stack ? `\n${v.stack}` : ""}`;
  if (typeof v === "string") return v;
  try {
    return JSON.stringify(v);
  } catch {
    return String(v);
  }
}

function flush() {
  timer = undefined;
  if (!queue.length) return;
  const body = scrub(JSON.stringify(queue.splice(0)));
  try {
    if (!navigator.sendBeacon?.("/api/logs", new Blob([body], { type: "application/json" }))) {
      fetch("/api/logs", { method: "POST", body, keepalive: true, headers: { "Content-Type": "application/json" } }).catch(() => {});
    }
  } catch {}
}

export function dlog(level: Level, kind: string, msg: string, data?: unknown) {
  if (typeof window === "undefined") return;
  queue.push({ ts: new Date().toISOString(), level, kind, msg: scrub(msg), data, page: location.pathname });
  if (level === "error" || queue.length >= 20) flush();
  else timer ??= setTimeout(flush, 1500);
}

export function installLogCapture() {
  if (installed || typeof window === "undefined") return;
  installed = true;
  for (const level of ["error", "warn"] as const) {
    const orig = console[level].bind(console);
    console[level] = (...args: unknown[]) => {
      orig(...args);
      dlog(level, "console", args.map(toText).join(" "));
    };
  }
  window.addEventListener("error", (e) =>
    dlog("error", "window.error", toText(e.error ?? e.message), { src: e.filename, line: e.lineno, col: e.colno }),
  );
  window.addEventListener("unhandledrejection", (e) => dlog("error", "unhandledrejection", toText(e.reason)));
  window.addEventListener("pagehide", flush);
  document.addEventListener("visibilitychange", () => document.visibilityState === "hidden" && flush());
  dlog("info", "session", "page loaded", { ua: navigator.userAgent, url: location.href });
}

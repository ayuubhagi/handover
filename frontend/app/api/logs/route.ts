// Keep runtime logs outside the Next.js project root. Writing them under
// frontend/ makes Turbopack refresh the page, which logs another page load and
// creates an infinite refresh loop.
// On in `next dev`; off in production builds unless HANDOVER_LOGS=1. HANDOVER_LOGS=0 always turns it off.
import { appendFile, mkdir, stat } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";

const DIR = path.join(tmpdir(), "handover-logs");
const FILE = path.join(DIR, "client.jsonl");
const MAX_FILE = 20 * 1024 * 1024;
const LEVELS = new Set(["info", "warn", "error"]);
const str = (v: unknown, max: number) => (typeof v === "string" ? v.slice(0, max) : undefined);

function enabled() {
  const flag = process.env.HANDOVER_LOGS;
  if (flag === "0") return false;
  return flag === "1" || process.env.NODE_ENV !== "production";
}

export async function POST(req: Request) {
  if (!enabled()) return new Response(null, { status: 404 });
  const text = await req.text().catch(() => "");
  if (!text || text.length > 256_000) return new Response(null, { status: 400 });
  let raw: unknown;
  try {
    raw = JSON.parse(text);
  } catch {
    return new Response(null, { status: 400 });
  }
  const entries = (Array.isArray(raw) ? raw : [raw]).slice(0, 100).flatMap((e) => {
    if (!e || typeof e !== "object") return [];
    const r = e as Record<string, unknown>;
    const level = str(r.level, 8);
    if (!level || !LEVELS.has(level)) return [];
    const data = r.data === undefined ? undefined : JSON.stringify(r.data).slice(0, 4000);
    return [{ ts: str(r.ts, 40), level, kind: str(r.kind, 40), msg: str(r.msg, 8000), page: str(r.page, 300), data }];
  });
  if (!entries.length) return new Response(null, { status: 400 });
  await mkdir(DIR, { recursive: true });
  const size = await stat(FILE).then((s) => s.size).catch(() => 0);
  if (size > MAX_FILE) return new Response(null, { status: 507 });
  await appendFile(FILE, entries.map((e) => JSON.stringify(e)).join("\n") + "\n");
  return new Response(null, { status: 204 });
}

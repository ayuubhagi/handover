// Appends browser debug logs to frontend/logs/client.jsonl (git-ignored). Set HANDOVER_LOGS=0 to turn off.
import { appendFile, mkdir } from "node:fs/promises";
import path from "node:path";

const DIR = path.join(process.cwd(), "logs");
const FILE = path.join(DIR, "client.jsonl");

export async function POST(req: Request) {
  if (process.env.HANDOVER_LOGS === "0") return new Response(null, { status: 204 });
  const text = await req.text().catch(() => "");
  if (!text || text.length > 512_000) return new Response(null, { status: 400 });
  let entries: unknown[];
  try {
    const parsed = JSON.parse(text);
    entries = Array.isArray(parsed) ? parsed : [parsed];
  } catch {
    return new Response(null, { status: 400 });
  }
  await mkdir(DIR, { recursive: true });
  await appendFile(FILE, entries.map((e) => JSON.stringify(e)).join("\n") + "\n");
  return new Response(null, { status: 204 });
}

// Names a conversation from its first message. Runs on the server so no key reaches the browser.
// Groq first (GROQ_API_KEY), Gemini as fallback (GOOGLE_API_KEY). With neither key, chats stay untitled.

const GROQ_MODEL = process.env.GROQ_TITLE_MODEL || "openai/gpt-oss-20b";
const GEMINI_MODEL = process.env.GEMINI_TITLE_MODEL || "gemini-flash-lite-latest";

const prompt = (text: string) =>
  `Write a 2 to 5 word title for a chat that starts with the message below. Plain words, sentence case, no quotes, no trailing punctuation. Reply with the title only.\n\nMessage: ${text.slice(0, 1200)}`;

async function fromGroq(key: string, text: string): Promise<string | null> {
  const r = await fetch("https://api.groq.com/openai/v1/chat/completions", {
    method: "POST",
    signal: AbortSignal.timeout(10_000),
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${key}` },
    body: JSON.stringify({
      model: GROQ_MODEL,
      messages: [{ role: "user", content: prompt(text) }],
      temperature: 0.3,
      max_completion_tokens: 300,
      ...(GROQ_MODEL.startsWith("openai/gpt-oss") ? { reasoning_effort: "low", include_reasoning: false } : {}),
    }),
  });
  if (!r.ok) return null;
  const j = await r.json();
  return j?.choices?.[0]?.message?.content ?? null;
}

async function fromGemini(key: string, text: string): Promise<string | null> {
  const r = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL}:generateContent`, {
    method: "POST",
    signal: AbortSignal.timeout(10_000),
    headers: { "Content-Type": "application/json", "x-goog-api-key": key },
    body: JSON.stringify({
      contents: [{ parts: [{ text: prompt(text) }] }],
      generationConfig: { temperature: 0.3, maxOutputTokens: 30 },
    }),
  });
  if (!r.ok) return null;
  const j = await r.json();
  return j?.candidates?.[0]?.content?.parts?.map((p: { text?: string }) => p.text ?? "").join("") ?? null;
}

function clean(raw: string): string {
  return raw.replace(/["“”*#]/g, "").replace(/[.!?]+$/, "").trim().split("\n")[0].slice(0, 60);
}

export async function POST(req: Request) {
  const { text } = (await req.json().catch(() => ({}))) as { text?: string };
  if (!text?.trim()) return Response.json({ title: null }, { status: 400 });

  const attempts: [string | undefined, typeof fromGroq][] = [
    [process.env.GROQ_API_KEY, fromGroq],
    [process.env.GOOGLE_API_KEY, fromGemini],
  ];
  for (const [key, call] of attempts) {
    if (!key) continue;
    try {
      const raw = await call(key, text);
      const title = raw ? clean(raw) : "";
      if (title) return Response.json({ title });
    } catch {
      // try the next provider
    }
  }
  // No key, or every provider failed: the chat keeps its default name. Not an error for the caller.
  return Response.json({ title: null });
}

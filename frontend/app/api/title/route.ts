// Names a conversation from its first message with Gemini. Runs on the server so the key never reaches the browser.

const MODEL = process.env.GEMINI_TITLE_MODEL || "gemini-flash-lite-latest";

export async function POST(req: Request) {
  const key = process.env.GOOGLE_API_KEY;
  const { text } = (await req.json().catch(() => ({}))) as { text?: string };
  if (!key || !text?.trim()) return Response.json({ title: null }, { status: key ? 400 : 503 });

  const prompt = `Write a 2 to 5 word title for a chat that starts with the message below. Plain words, sentence case, no quotes, no trailing punctuation.\n\nMessage: ${text.slice(0, 1200)}`;
  try {
    const r = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${MODEL}:generateContent`, {
      method: "POST",
      signal: AbortSignal.timeout(10_000),
      headers: { "Content-Type": "application/json", "x-goog-api-key": key },
      body: JSON.stringify({ contents: [{ parts: [{ text: prompt }] }], generationConfig: { temperature: 0.3, maxOutputTokens: 30 } }),
    });
    if (!r.ok) return Response.json({ title: null }, { status: 502 });
    const j = await r.json();
    const raw: string = j?.candidates?.[0]?.content?.parts?.map((p: { text?: string }) => p.text ?? "").join("") ?? "";
    const title = raw.replace(/["“”*#]/g, "").replace(/[.!?]+$/, "").trim().split("\n")[0].slice(0, 60);
    return Response.json({ title: title || null });
  } catch {
    return Response.json({ title: null }, { status: 502 });
  }
}

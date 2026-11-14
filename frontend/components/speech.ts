"use client";

import { api } from "../lib/api";

/** Play an interviewer/answer clip; if there is no recording, read the text with the browser voice. Resolves when done. */
export function speak(url: string | null, text: string, onStart?: (stop: () => void) => void): Promise<void> {
  const src = api.mediaUrl(url);
  return new Promise((resolve) => {
    if (src) {
      const a = new window.Audio(src);
      a.onended = () => resolve();
      a.onerror = () => resolve();
      onStart?.(() => {
        a.pause();
        resolve();
      });
      a.play().catch(() => resolve());
      return;
    }
    if (typeof window !== "undefined" && "speechSynthesis" in window && text) {
      window.speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(text);
      u.rate = 1.02;
      u.onend = () => resolve();
      u.onerror = () => resolve();
      onStart?.(() => {
        window.speechSynthesis.cancel();
        resolve();
      });
      window.speechSynthesis.speak(u);
      return;
    }
    resolve();
  });
}

type Rec = { start(): void; stop(): void; abort(): void; onresult: ((e: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null; onend: (() => void) | null; onerror: (() => void) | null; interimResults: boolean; lang: string };

/** Browser dictation (Web Speech API), used for spoken questions in Ask mode. Null when unsupported. */
export function dictation(): Rec | null {
  if (typeof window === "undefined") return null;
  const w = window as unknown as { SpeechRecognition?: new () => Rec; webkitSpeechRecognition?: new () => Rec };
  const C = w.SpeechRecognition ?? w.webkitSpeechRecognition;
  if (!C) return null;
  const r = new C();
  r.interimResults = true;
  r.lang = "en-US";
  return r;
}

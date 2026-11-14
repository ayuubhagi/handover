"use client";

import { useEffect, useRef, useState } from "react";
import { api, errorMessage } from "../lib/api";
import type { Gap, Memory } from "../lib/types";
import { Audio, Button, Card, ErrorNote, MemoryMeta, Tag } from "./ui";

interface TurnView {
  question: string;
  transcript: string;
  memories: Memory[];
  gaps: Gap[];
  used: string[];
}

export function Interview({ onChange }: { onChange: () => void }) {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [question, setQuestion] = useState<{ text: string; audio: string | null } | null>(null);
  const [turns, setTurns] = useState<TurnView[]>([]);
  const [busy, setBusy] = useState<"start" | "upload" | null>(null);
  const [recording, setRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const recorder = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);
  const audioEl = useRef<HTMLAudioElement | null>(null);

  // Play the interviewer's question when a new audio URL arrives.
  useEffect(() => {
    const src = api.mediaUrl(question?.audio ?? null);
    if (!src) return;
    const a = new window.Audio(src);
    audioEl.current = a;
    a.play().catch(() => {});
    return () => a.pause();
  }, [question?.audio]);

  async function start() {
    setBusy("start");
    setError(null);
    try {
      const r = await api.startSession("u_expert");
      setSessionId(r.session_id);
      setQuestion({ text: r.first_question_text, audio: r.first_question_audio_url });
      setTurns([]);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(null);
    }
  }

  async function startRecording() {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const rec = new MediaRecorder(stream);
      chunks.current = [];
      rec.ondataavailable = (e) => e.data.size && chunks.current.push(e.data);
      rec.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        upload(new Blob(chunks.current, { type: rec.mimeType || "audio/webm" }));
      };
      audioEl.current?.pause();
      rec.start();
      recorder.current = rec;
      setRecording(true);
    } catch (e) {
      setError(`Microphone unavailable: ${errorMessage(e)}`);
    }
  }

  function stopRecording() {
    recorder.current?.stop();
    setRecording(false);
  }

  async function upload(blob: Blob) {
    if (!sessionId || !question) return;
    setBusy("upload");
    try {
      const r = await api.answer(sessionId, blob);
      setTurns((t) => [
        { question: question.text, transcript: r.transcript, memories: r.memories_created, gaps: r.gaps_created, used: r.used_memory_ids },
        ...t,
      ]);
      setQuestion({ text: r.next_question_text, audio: r.next_question_audio_url });
      onChange();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(null);
    }
  }

  return (
    <Card title="Interview" aside={sessionId && <span className="font-mono text-xs text-muted">{sessionId}</span>}>
      {!sessionId ? (
        <div className="flex flex-col items-start gap-3">
          <p className="text-sm text-muted">Start a session. The interviewer begins with open gaps and contradictions from earlier sessions.</p>
          <Button onClick={start} disabled={busy === "start"}>
            {busy === "start" ? "Starting…" : "Start interview"}
          </Button>
        </div>
      ) : (
        <div className="space-y-5">
          {question && (
            <div className="rounded-lg bg-accent-soft p-4">
              <p className="text-xs font-medium uppercase tracking-wide text-accent">Interviewer asks</p>
              <p className="mt-1 font-serif text-lg leading-snug">{question.text}</p>
              {question.audio && (
                <div className="mt-3">
                  <Audio url={question.audio} />
                </div>
              )}
            </div>
          )}
          <div className="flex items-center gap-3">
            {!recording ? (
              <Button onClick={startRecording} disabled={busy === "upload"}>
                {busy === "upload" ? "Processing answer…" : "Record answer"}
              </Button>
            ) : (
              <Button variant="danger" onClick={stopRecording}>
                <span className="mr-2 inline-block h-2 w-2 animate-pulse rounded-full bg-white" />
                Stop and send
              </Button>
            )}
            <Button variant="ghost" onClick={start} disabled={!!busy || recording}>
              New session
            </Button>
          </div>
        </div>
      )}
      {error && (
        <div className="mt-4">
          <ErrorNote message={error} />
        </div>
      )}
      {turns.length > 0 && (
        <ol className="mt-6 space-y-4 border-t border-line pt-5">
          {turns.map((t, i) => (
            <li key={turns.length - i} className="space-y-2 text-sm">
              <p className="text-muted">Q: {t.question}</p>
              <p>
                <span className="font-medium">Dana:</span> “{t.transcript}”
              </p>
              {t.used.length > 0 && <p className="text-xs text-muted">Question drew on memories {t.used.join(", ")}</p>}
              {t.memories.map((m) => (
                <div key={m.id} className="rounded-md border border-line p-3">
                  <p className="mb-1 text-xs font-medium text-accent">New memory</p>
                  <p>{m.text}</p>
                  <div className="mt-2">
                    <MemoryMeta m={m} />
                  </div>
                </div>
              ))}
              {t.gaps.map((g) => (
                <div key={g.id} className="rounded-md border border-warn/30 bg-warn-soft p-3">
                  <Tag>{g.kind}</Tag> <span className="ml-1">{g.question}</span>
                </div>
              ))}
            </li>
          ))}
        </ol>
      )}
    </Card>
  );
}

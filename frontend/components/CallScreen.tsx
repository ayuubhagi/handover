"use client";

import { useEffect, useRef, useState } from "react";
import type { AnswerResponse } from "../lib/types";
import { Bars } from "./Composer";
import { IconMic, IconMicOff, IconPhoneOff } from "./icons";
import { speak } from "./speech";
import { chats, type Conversation } from "./store";
import { useRecorder } from "./useRecorder";
import { MochiHeadphonesSticker } from "stick-it-up";

type Phase = "connecting" | "speaking" | "listening" | "thinking" | "error";

const LABEL: Record<Phase, string> = {
  connecting: "Connecting",
  speaking: "Handover is asking",
  listening: "Your turn. Take your time.",
  thinking: "Saving what you said",
  error: "Something went wrong",
};

export function CallScreen({
  conversation,
  start,
  answer,
  onEnd,
}: {
  conversation: Conversation | null;
  start: () => Promise<Conversation | null>;
  answer: (c: Conversation, blob: Blob | null) => Promise<AnswerResponse | null>;
  onEnd: () => void;
}) {
  const [phase, setPhase] = useState<Phase>("connecting");
  const [question, setQuestion] = useState("");
  const [saved, setSaved] = useState<string[]>([]);
  const [muted, setMuted] = useState(false);
  const [secs, setSecs] = useState(0);
  const rec = useRecorder();
  const conv = useRef<Conversation | null>(conversation);
  const ended = useRef(false);
  const stopSpeech = useRef<(() => void) | null>(null);
  const recRef = useRef(rec);
  useEffect(() => {
    recRef.current = rec;
  });

  async function ask(text: string, audio: string | null) {
    if (ended.current) return;
    setQuestion(text);
    setPhase("speaking");
    await speak(audio, text, (s) => (stopSpeech.current = s));
    if (ended.current) return;
    setPhase("listening");
    const ok = await recRef.current.start();
    if (!ok) setPhase("error");
  }

  async function doneTalking() {
    const blob = await rec.stop();
    if (!conv.current || ended.current) return;
    setPhase("thinking");
    const r = await answer(conv.current, blob);
    conv.current = chats.get().conversations.find((c) => c.id === conv.current!.id) ?? conv.current;
    if (!r) return setPhase("error");
    if (r.memories_created.length) setSaved((s) => [...r.memories_created.map((m) => m.text), ...s].slice(0, 3));
    ask(r.next_question_text, r.next_question_audio_url);
  }

  const askRef = useRef(ask);
  useEffect(() => {
    askRef.current = ask;
  });
  useEffect(() => {
    let c = conv.current;
    (async () => {
      if (!c?.sessionId || c.mode !== "interview") c = await start();
      if (!c) return setPhase("error");
      conv.current = c;
      const last = [...c.messages].reverse().find((m) => m.role === "interviewer");
      if (last && last.role === "interviewer") askRef.current(last.text, last.audio);
    })();
    const t = setInterval(() => setSecs((s) => s + 1), 1000);
    return () => {
      ended.current = true;
      clearInterval(t);
      stopSpeech.current?.();
      recRef.current.cancel();
    };
    // Runs once per call.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function toggleMute() {
    rec.mute(!muted);
    setMuted(!muted);
  }

  const time = `${Math.floor(secs / 60)}:${String(secs % 60).padStart(2, "0")}`;
  const listening = phase === "listening";

  return (
    <div className="relative flex h-full flex-col items-center justify-between overflow-hidden px-6 py-10">
      <div className="relative text-center">
        <p className="text-sm font-medium">Recording call</p>
        <p className="mt-0.5 font-mono text-xs text-soft">{time}</p>
      </div>

      <div className="relative flex w-full max-w-xl flex-col items-center text-center">
        <div className="relative grid h-40 w-40 place-items-center">
          {phase === "speaking" && (
            <>
              <span className="orb-ring" />
              <span className="orb-ring" />
              <span className="orb-ring" />
            </>
          )}
          <div
            className={`orb grid h-32 w-32 place-items-center rounded-full bg-accent shadow-[0_0_80px_var(--glow-a)] transition-transform ${listening ? "" : ""}`}
            style={listening ? { transform: `scale(${1 + rec.level * 0.25})`, animation: "none" } : undefined}
          >
            {listening ? <Bars level={muted ? 0 : rec.level} count={9} className="h-10" /> : <MochiHeadphonesSticker size={78} />}
          </div>
        </div>
        <p className="mt-8 text-sm font-medium text-accent-ink" aria-live="polite">
          {muted && listening ? "Muted" : LABEL[phase]}
        </p>
        <p className="mt-3 min-h-[3.5rem] font-serif text-2xl leading-snug">{question}</p>
        {(rec.error || phase === "error") && <p className="mt-3 text-sm text-danger">{rec.error ?? "Couldn’t connect. End the call and try again."}</p>}
        {saved.length > 0 && (
          <div className="mt-6 flex flex-col items-center gap-1.5">
            {saved.map((s) => (
              <span key={s} className="max-w-full truncate rounded-full bg-ok-soft px-3 py-1 text-xs text-ok">
                ✓ Saved: {s}
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="relative flex items-center gap-5">
        <button
          onClick={toggleMute}
          aria-label={muted ? "Unmute" : "Mute"}
          aria-pressed={muted}
          className={`grid h-14 w-14 place-items-center rounded-full border border-line transition ${muted ? "bg-primary text-on-primary" : "glass text-ink hover:bg-hover"}`}
        >
          {muted ? <IconMicOff className="h-5 w-5" /> : <IconMic className="h-5 w-5" />}
        </button>
        <button
          onClick={doneTalking}
          disabled={!listening}
          className="h-14 rounded-full bg-primary px-7 text-sm font-medium text-on-primary transition hover:opacity-90 disabled:opacity-30"
        >
          I’m done answering
        </button>
        <button onClick={onEnd} aria-label="End call" className="grid h-14 w-14 place-items-center rounded-full bg-danger text-white transition hover:opacity-90">
          <IconPhoneOff className="h-5 w-5" />
        </button>
      </div>
    </div>
  );
}

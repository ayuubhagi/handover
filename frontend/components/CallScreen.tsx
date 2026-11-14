"use client";

import { useEffect, useRef, useState } from "react";
import type { AnswerResponse, AskResponse } from "../lib/types";
import { Bars } from "./Composer";
import { IconMic, IconMicOff, IconPhoneOff } from "./icons";
import { dictation, speak } from "./speech";
import { chats, type Conversation } from "./store";
import { useRecorder } from "./useRecorder";
import { MochiHeadphonesSticker } from "stick-it-up";

type Phase = "connecting" | "speaking" | "listening" | "thinking" | "error";

const LABELS: Record<"interview" | "ask", Record<Phase, string>> = {
  interview: {
    connecting: "Connecting",
    speaking: "Asking",
    listening: "Listening, just talk",
    thinking: "Filing it",
    error: "Something went wrong",
  },
  ask: {
    connecting: "Connecting",
    speaking: "Answering",
    listening: "Listening, ask anything",
    thinking: "Checking the books",
    error: "Something went wrong",
  },
};

type Props =
  | {
      kind: "interview";
      conversation: Conversation | null;
      start: () => Promise<Conversation | null>;
      answer: (c: Conversation, blob: Blob | null) => Promise<AnswerResponse | null>;
      onEnd: () => void;
    }
  | {
      kind: "ask";
      ask: (question: string) => Promise<AskResponse | null>;
      onEnd: () => void;
    };

/**
 * Hands-free voice call. It speaks, then listens; when you stop talking for a
 * moment it sends your turn on its own and speaks the reply. "Send now" skips the wait.
 */
export function CallScreen(props: Props) {
  const { kind, onEnd } = props;
  const [phase, setPhase] = useState<Phase>("connecting");
  const [caption, setCaption] = useState("");
  const [heard, setHeard] = useState("");
  const [saved, setSaved] = useState<string[]>([]);
  const [muted, setMuted] = useState(false);
  const [secs, setSecs] = useState(0);
  const [err, setErr] = useState<string | null>(null);
  const rec = useRecorder({ onSilence: () => turnRef.current() });
  const conv = useRef<Conversation | null>(kind === "interview" ? props.conversation : null);
  const ended = useRef(false);
  const inTurn = useRef(false);
  const stopSpeech = useRef<(() => void) | null>(null);
  const recog = useRef<ReturnType<typeof dictation>>(null);
  const said = useRef("");
  const mutedRef = useRef(false);
  const recRef = useRef(rec);
  const propsRef = useRef(props);
  useEffect(() => {
    recRef.current = rec;
    propsRef.current = props;
  });

  /** Speak something, then open the mic for the person's turn. */
  async function sayThenListen(text: string, audio: string | null, after?: { url: string | null; text: string }) {
    if (ended.current) return;
    setCaption(text);
    setPhase("speaking");
    await speak(audio, text, (s) => (stopSpeech.current = s));
    // In Ask, follow the answer with the expert's own recorded words.
    if (after?.url && !ended.current) await speak(after.url, after.text, (s) => (stopSpeech.current = s));
    stopSpeech.current = null;
    if (ended.current) return;
    await listen();
  }

  async function listen() {
    setHeard("");
    said.current = "";
    inTurn.current = false;
    if (kind === "ask") {
      const r = dictation();
      if (!r) {
        setErr("Voice questions need Chrome or Edge.");
        return setPhase("error");
      }
      r.continuous = true;
      r.onresult = (e) => {
        if (mutedRef.current) return;
        let t = "";
        for (let i = 0; i < e.results.length; i++) t += e.results[i][0].transcript;
        said.current = t;
        setHeard(t);
      };
      r.onend = () => {};
      r.onerror = () => {};
      recog.current = r;
      try {
        r.start();
      } catch {}
    }
    setPhase("listening");
    const ok = await recRef.current.start();
    if (!ok) setPhase("error");
  }

  /** End of the person's turn: send it and play the reply. */
  async function endTurn() {
    if (inTurn.current || ended.current) return;
    inTurn.current = true;
    const blob = await recRef.current.stop();
    if (ended.current) return;
    const p = propsRef.current;

    if (p.kind === "ask") {
      const r = recog.current;
      recog.current = null;
      // Give the recogniser a beat to finalise the last words.
      await new Promise((res) => setTimeout(res, 350));
      try {
        r?.stop();
      } catch {}
      const q = said.current.trim();
      if (!q) return listen();
      setPhase("thinking");
      const a = await p.ask(q);
      if (!a) {
        setErr("Couldn’t get an answer. Try asking again.");
        return listen();
      }
      setErr(null);
      const top = a.sources[0];
      return sayThenListen(a.answer_text, null, top ? { url: top.clip_url, text: top.transcript ?? top.memory.text } : undefined);
    }

    if (!conv.current || !blob) return listen();
    setPhase("thinking");
    const r = await p.answer(conv.current, blob);
    conv.current = chats.get().conversations.find((c) => c.id === conv.current!.id) ?? conv.current;
    if (!r) {
      setErr("That didn’t go through. Say it again.");
      return listen();
    }
    setErr(null);
    if (r.transcript) setHeard(r.transcript);
    if (r.memories_created.length) setSaved((s) => [...r.memories_created.map((m) => m.text), ...s].slice(0, 3));
    sayThenListen(r.next_question_text, r.next_question_audio_url);
  }

  const turnRef = useRef(endTurn);
  const sayRef = useRef(sayThenListen);
  useEffect(() => {
    turnRef.current = endTurn;
    sayRef.current = sayThenListen;
  });

  const starting = useRef<Promise<Conversation | null> | null>(null);
  useEffect(() => {
    ended.current = false;
    (async () => {
      const p = propsRef.current;
      if (p.kind === "ask") return sayRef.current("Hi, what do you need to know about the desk?", null);
      let c = conv.current;
      // Dev mode mounts twice; share one session instead of starting two.
      if (!c?.sessionId || c.mode !== "interview") c = await (starting.current ??= p.start());
      if (ended.current) return;
      if (!c) return setPhase("error");
      conv.current = c;
      const last = [...c.messages].reverse().find((m) => m.role === "interviewer");
      if (last && last.role === "interviewer") sayRef.current(last.text, last.audio);
      else sayRef.current("I’m listening. Walk me through how you run the money.", null);
    })();
    const t = setInterval(() => setSecs((s) => s + 1), 1000);
    return () => {
      ended.current = true;
      clearInterval(t);
      stopSpeech.current?.();
      recRef.current.cancel();
      try {
        recog.current?.abort();
      } catch {}
    };
    // Runs once per call.
  }, []);

  function toggleMute() {
    mutedRef.current = !muted;
    rec.mute(!muted);
    setMuted(!muted);
  }

  /** Tap the orb while it talks to cut in. */
  function interrupt() {
    if (phase === "speaking") stopSpeech.current?.();
  }

  const time = `${Math.floor(secs / 60)}:${String(secs % 60).padStart(2, "0")}`;
  const listening = phase === "listening";
  const labels = LABELS[kind];

  return (
    <div className="relative flex h-full flex-col items-center justify-between overflow-hidden px-6 py-10">
      <div className="relative text-center">
        <p className="text-sm font-medium">{kind === "interview" ? "Recording call" : "Ask call"}</p>
        <p className="mt-0.5 font-mono text-xs text-soft">{time}</p>
      </div>

      <div className="relative flex w-full max-w-xl flex-col items-center text-center">
        <button
          type="button"
          onClick={interrupt}
          aria-label={phase === "speaking" ? "Interrupt" : undefined}
          tabIndex={phase === "speaking" ? 0 : -1}
          className="relative grid h-40 w-40 place-items-center"
        >
          {phase === "speaking" && (
            <>
              <span className="orb-ring" />
              <span className="orb-ring" />
              <span className="orb-ring" />
            </>
          )}
          <span
            className="orb grid h-32 w-32 place-items-center rounded-full bg-accent shadow-[0_0_80px_var(--glow-a)] transition-transform"
            style={listening ? { transform: `scale(${1 + rec.level * 0.25})`, animation: "none" } : undefined}
          >
            {listening ? <Bars level={muted ? 0 : rec.level} count={9} className="h-10" /> : <MochiHeadphonesSticker size={78} />}
          </span>
        </button>
        <p className="mt-8 text-sm font-medium text-accent-ink" aria-live="polite">
          {muted && listening ? "Muted" : labels[phase]}
        </p>
        <p className="mt-3 min-h-[3.5rem] max-h-48 overflow-y-auto font-serif text-2xl leading-snug">{caption}</p>
        {heard && <p className="mt-3 max-w-full text-sm text-muted">“{heard}”</p>}
        {(rec.error || err || phase === "error") && (
          <p className="mt-3 text-sm text-danger">{rec.error ?? err ?? "Couldn’t connect. End the call and try again."}</p>
        )}
        {saved.length > 0 && (
          <div className="mt-6 flex flex-col items-center gap-1.5">
            {saved.map((s) => (
              <span key={s} className="max-w-full truncate rounded-full bg-ok-soft px-3 py-1 text-xs text-ok">
                {s}
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
          onClick={() => endTurn()}
          disabled={!listening}
          className="h-14 rounded-full border border-line px-6 text-sm font-medium text-muted transition hover:bg-hover disabled:opacity-30"
        >
          Send now
        </button>
        <button onClick={onEnd} aria-label="End call" className="grid h-14 w-14 place-items-center rounded-full bg-danger text-white transition hover:opacity-90">
          <IconPhoneOff className="h-5 w-5" />
        </button>
      </div>
    </div>
  );
}

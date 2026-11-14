"use client";

import { useEffect, useRef, useState } from "react";
import { api, errorMessage } from "../lib/api";
import { useUserId } from "../lib/hooks";
import { setUserId } from "../lib/session";
import { NoriHeadphonesSticker, PipDetectiveSticker } from "stick-it-up";
import { CallScreen } from "./CallScreen";
import { Composer } from "./Composer";
import { IconLock } from "./icons";
import { chats, uid, useChats, type Conversation, type Message } from "./store";
import { Button, ErrorNote, PlayButton } from "./ui";
import type { Mode } from "./store";

const SUGGESTIONS = [
  "When should I restart the payments queue?",
  "What do I do when SWIFT messages are stuck?",
  "Anything odd about the Northwind Freight file?",
];


export function Chat() {
  const user = useUserId();
  const { conversations, activeId, mode: selectedMode } = useChats();
  const active = conversations.find((c) => c.id === activeId) ?? null;
  const mode = active?.mode ?? selectedMode;
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState<string | null>(null);
  const [calling, setCalling] = useState(false);
  const scroller = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: "smooth" });
  }, [active?.messages.length, pending, busy]);

  const push = (id: string, ...m: Message[]) => chats.update(id, (c) => ({ ...c, messages: [...c.messages, ...m] }));

  async function startInterview(): Promise<Conversation | null> {
    setError(null);
    setBusy("Starting");
    try {
      const r = await api.startSession("u_expert");
      const id = chats.create({
        mode: "interview",
        user,
        title: `Interview, ${new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}`,
        sessionId: r.session_id,
        messages: [{ id: uid(), role: "interviewer", text: r.first_question_text, audio: r.first_question_audio_url }],
      });
      return chats.get().conversations.find((c) => c.id === id) ?? null;
    } catch (e) {
      setError(errorMessage(e));
      return null;
    } finally {
      setBusy(null);
    }
  }

  /** Send an interview answer (voice blob or typed text). Returns the next question for the call screen. */
  async function answer(conv: Conversation, blob: Blob | null, text?: string) {
    if (!conv.sessionId) return null;
    setError(null);
    setPending(text ?? "Voice answer");
    setBusy("Listening back");
    try {
      const r = await api.answer(conv.sessionId, blob, text);
      push(
        conv.id,
        { id: uid(), role: "you", text: r.transcript || text || "", saved: r.memories_created },
        { id: uid(), role: "interviewer", text: r.next_question_text, audio: r.next_question_audio_url },
      );
      return r;
    } catch (e) {
      setError(errorMessage(e));
      return null;
    } finally {
      setPending(null);
      setBusy(null);
    }
  }

  async function ask(q: string) {
    setError(null);
    let id = active?.id;
    if (!id) id = chats.create({ mode: "ask", user, title: q, sessionId: null, messages: [] });
    push(id, { id: uid(), role: "you", text: q });
    setBusy("Thinking");
    try {
      const r = await api.ask(q, true);
      push(id, { id: uid(), role: "answer", answer: r, question: q });
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(null);
    }
  }

  const notExpert = mode === "interview" && user !== "u_expert";
  const empty = !active || active.messages.length === 0;

  if (calling) {
    return (
      <CallScreen
        conversation={active}
        start={startInterview}
        answer={answer}
        onEnd={() => setCalling(false)}
      />
    );
  }

  const switchMode = (m: Mode) => {
    if (m !== mode) chats.setMode(m);
  };
  const shared = { mode, onMode: switchMode };

  const composer =
    mode === "ask" ? (
      <Composer
        {...shared}
        placeholder="Ask anything that was handed over"
        disabled={!!busy}
        onSend={ask}
        autoFocus
      />
    ) : (
      <Composer
        {...shared}
        placeholder={empty ? "Start with what you do day to day" : "Type your answer, or speak it"}
        disabled={!!busy || notExpert}
        onSend={async (t) => {
          const conv = active?.sessionId ? active : await startInterview();
          if (conv) answer(conv, null, t);
        }}
        onCall={() => setCalling(true)}
        autoFocus
      />
    );

  const errors = error && (
    <div className="mx-auto mb-3 w-full max-w-2xl">
      <ErrorNote message={error} />
    </div>
  );

  if (empty) {
    const recording = mode === "interview";
    return (
      <div className="relative flex h-full flex-col items-center justify-center px-4">
        <div className="relative w-full max-w-2xl">
          <div className="mb-6 flex justify-center">
            <span className="sticker-float -rotate-6">
              {recording ? <NoriHeadphonesSticker size={88} peel /> : <PipDetectiveSticker size={88} peel />}
            </span>
          </div>
          <h1 className="text-balance text-center font-serif text-4xl tracking-tight sm:text-5xl">
            {recording ? "What do you know that nobody else does?" : "What do you need to know?"}
          </h1>
          <div className="mt-8">
            {errors}
            {notExpert ? <ExpertOnly /> : composer}
            {mode === "ask" && (
              <div className="mt-4 flex flex-wrap justify-center gap-2">
                {SUGGESTIONS.map((s) => (
                  <button key={s} onClick={() => ask(s)} disabled={!!busy} className="glass rounded-full border border-line px-3.5 py-1.5 text-sm text-muted transition hover:bg-hover hover:text-ink">
                    {s}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <div ref={scroller} className="min-h-0 flex-1 overflow-y-auto px-4 pt-14 md:pt-8">
        <div className="mx-auto w-full max-w-2xl space-y-5 pb-8">
          {active!.messages.map((m) => (
            <Bubble key={m.id} m={m} />
          ))}
          {pending && (
            <div className="flex justify-end opacity-60">
              <div className="max-w-[85%] rounded-3xl rounded-br-lg bg-hover px-4 py-2.5 text-[15px]">{pending}</div>
            </div>
          )}
          {busy && (
            <div className="dots py-2" aria-label={busy}>
              <span />
              <span />
              <span />
            </div>
          )}
        </div>
      </div>
      <div className="px-4 pb-5">
        {errors}
        <div className="mx-auto w-full max-w-2xl">{notExpert ? <ExpertOnly /> : composer}</div>
      </div>
    </div>
  );
}

function ExpertOnly() {
  return (
    <div className="glass flex flex-col items-center gap-3 rounded-2xl border border-line px-4 py-5 text-center text-sm text-muted">
      <p>Recording is for the person handing over. Switch roles to record, or ask instead.</p>
      <Button variant="ghost" onClick={() => setUserId("u_expert")}>
        Switch to Handing over
      </Button>
    </div>
  );
}

function Bubble({ m }: { m: Message }) {
  if (m.role === "you") {
    return (
      <div className="msg-in flex flex-col items-end gap-1.5">
        <div className="max-w-[85%] whitespace-pre-wrap rounded-3xl rounded-br-lg bg-active px-4 py-2.5 text-[15px] leading-relaxed">{m.text}</div>
        {m.saved?.map((s) => (
          <span key={s.id} className="inline-flex max-w-[85%] items-center gap-1.5 rounded-full bg-ok-soft px-2.5 py-1 text-xs text-ok">
            <span aria-hidden="true">✓</span>
            <span className="truncate">Saved: {s.text}</span>
          </span>
        ))}
      </div>
    );
  }
  if (m.role === "interviewer") {
    return (
      <div className="msg-in flex gap-3">
        <Avatar />
        <div className="min-w-0 flex-1 space-y-2">
          <p className="font-serif text-[17px] leading-relaxed">{m.text}</p>
          <PlayButton url={m.audio} text={m.text} label="Listen" />
        </div>
      </div>
    );
  }
  if (m.role === "answer") {
    const r = m.answer;
    return (
      <div className="msg-in flex gap-3">
        <Avatar />
        <div className="min-w-0 flex-1 space-y-3">
          <p className="whitespace-pre-wrap font-serif text-[17px] leading-relaxed">{r.answer_text}</p>
          {r.sources.length > 0 && (
            <div className="space-y-2">
              {r.sources.map((s) => (
                <div key={s.memory.id} className="rounded-2xl border border-line bg-surface px-4 py-3">
                  {s.transcript && <p className="text-sm text-muted">“{s.transcript}”</p>}
                  <div className={s.transcript ? "mt-2" : ""}>
                    <PlayButton url={s.clip_url} text={s.transcript ?? s.memory.text} label="Play the original" />
                  </div>
                </div>
              ))}
            </div>
          )}
          {r.blocked_count > 0 && (
            <p className="flex items-center gap-1.5 text-sm text-soft">
              <IconLock className="h-3.5 w-3.5" />
              Some notes aren’t shared with you.
            </p>
          )}
        </div>
      </div>
    );
  }
  return <p className="text-center text-sm text-soft">{m.text}</p>;
}

function Avatar() {
  return <span className="mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-full bg-accent font-serif text-sm text-on-accent">h</span>;
}

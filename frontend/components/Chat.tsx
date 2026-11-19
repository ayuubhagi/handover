"use client";

import { useEffect, useRef, useState } from "react";
import { api, errorMessage } from "../lib/api";
import { useUserId } from "../lib/hooks";
import { NoriRocketSticker } from "stick-it-up";
import { CallScreen } from "./CallScreen";
import { Composer } from "./Composer";
import { HandoverProgress } from "./HandoverProgress";
import { IconLock } from "./icons";
import { Logo } from "./Logo";
import { chats, uid, useChats, type Conversation, type Message } from "./store";
import { ErrorNote, PlayButton, withheldText } from "./ui";
import type { Mode } from "./store";
import type { AskResponse } from "../lib/types";

/** Ask the title route (Groq, then Gemini) for a short title; keeps the fallback if it fails. */
async function nameConversation(id: string, text: string) {
  try {
    const r = await fetch("/api/title", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text }) });
    const j = (await r.json()) as { title: string | null };
    if (j.title) chats.update(id, (c) => ({ ...c, title: j.title! }));
  } catch {}
}

const fallbackTitle = (t: string) => (t.length > 40 ? `${t.slice(0, 40).trimEnd()}…` : t);


export function Chat() {
  const user = useUserId();
  const { conversations, activeId, mode: selectedMode } = useChats();
  const active = conversations.find((c) => c.id === activeId) ?? null;
  const isSenior = user === "u_expert";
  // Only Dana records. Everyone else is ask-only.
  const mode: Mode = isSenior ? (active?.mode ?? selectedMode) : "ask";
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState<string | null>(null);
  const [calling, setCalling] = useState(false);
  const [progressKey, setProgressKey] = useState(0);
  const scroller = useRef<HTMLDivElement>(null);

  // A role switch ends any call and drops state from the previous viewer.
  const [viewer, setViewer] = useState(user);
  if (viewer !== user) {
    setViewer(user);
    setCalling(false);
    setError(null);
    setPending(null);
  }

  // Give old timestamp-named chats ("Interview, 1:18 PM") a real name.
  useEffect(() => {
    for (const c of conversations) {
      if (!/^Interview, |^New recording$/.test(c.title)) continue;
      const first = c.messages.find((m) => m.role === "you") ?? c.messages.find((m) => m.role === "interviewer");
      if (first && "text" in first && first.text) nameConversation(c.id, first.text);
    }
    // Once per load.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversations.length > 0]);

  useEffect(() => {
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: "smooth" });
  }, [active?.messages.length, pending, busy]);

  const push = (id: string, ...m: Message[]) => chats.update(id, (c) => ({ ...c, messages: [...c.messages, ...m] }));

  async function startInterview(lead?: string): Promise<Conversation | null> {
    setError(null);
    setBusy("Starting");
    try {
      const r = await api.startSession("u_expert");
      const id = chats.create({
        mode: "interview",
        user,
        title: lead ? fallbackTitle(lead) : "New recording",
        sessionId: r.session_id,
        // When the person leads with their own words, don't open with a canned question.
        messages: lead ? [] : [{ id: uid(), role: "interviewer", text: r.first_question_text, audio: r.first_question_audio_url }],
      });
      if (lead) nameConversation(id, lead);
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
      setProgressKey((k) => k + 1);
      return r;
    } catch (e) {
      setError(errorMessage(e));
      return null;
    } finally {
      setPending(null);
      setBusy(null);
    }
  }

  async function ask(q: string): Promise<AskResponse | null> {
    setError(null);
    let id = chats.get().conversations.find((c) => c.id === chats.get().activeId && c.mode === "ask")?.id;
    if (!id) {
      id = chats.create({ mode: "ask", user, title: fallbackTitle(q), sessionId: null, messages: [] });
      nameConversation(id, q);
    }
    push(id, { id: uid(), role: "you", text: q });
    setBusy("Thinking");
    try {
      const r = await api.ask(q, true);
      push(id, { id: uid(), role: "answer", answer: r, question: q });
      return r;
    } catch (e) {
      setError(errorMessage(e));
      return null;
    } finally {
      setBusy(null);
    }
  }

  const empty = !active || active.messages.length === 0;

  if (calling) {
    return mode === "ask" ? (
      <CallScreen kind="ask" ask={ask} onEnd={() => setCalling(false)} />
    ) : (
      <CallScreen kind="interview" conversation={active} start={startInterview} answer={answer} onEnd={() => setCalling(false)} />
    );
  }

  const switchMode = (m: Mode) => {
    if (m !== mode) chats.setMode(m);
  };
  const shared = { mode, onMode: isSenior ? switchMode : undefined };
  const progress = isSenior && <HandoverProgress refreshKey={progressKey} />;

  const composer =
    mode === "ask" ? (
      <Composer
        {...shared}
        placeholder="Ask anything"
        disabled={!!busy}
        onSend={ask}
        onCall={() => setCalling(true)}
        autoFocus
      />
    ) : (
      <Composer
        {...shared}
        placeholder={empty ? "Tell it how you run the desk" : "Your answer"}
        disabled={!!busy}
        onSend={async (t) => {
          const conv = active?.sessionId ? active : await startInterview(t);
          return conv ? answer(conv, null, t) : null;
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
    return (
      <div className="flex h-full flex-col overflow-y-auto px-4">
        {progress && <div className="shrink-0 pt-16">{progress}</div>}
        <div className="mx-auto my-auto w-full max-w-2xl py-8">
          <h1 className="text-balance text-center font-serif text-4xl tracking-tight sm:text-5xl">
            {mode === "interview" ? "What should the next banker know?" : "What do you need to know?"}
          </h1>
          <div className="mt-8">
            {errors}
            {composer}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {progress && <div className="px-4 pt-16">{progress}</div>}
      <div ref={scroller} className={`min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 ${progress ? "pt-4" : "pt-16"}`}>
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
        <div className="mx-auto w-full max-w-2xl">{composer}</div>
      </div>
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
            <span className="sticker-icon h-3.5 w-3.5">
              <NoriRocketSticker size={14} />
            </span>
            <span className="truncate">{s.text}</span>
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
                    <PlayButton url={s.clip_url} text={s.transcript ?? s.memory.text} label="Original" />
                  </div>
                </div>
              ))}
            </div>
          )}
          {r.blocked_count > 0 && (
            <p className="flex items-center gap-1.5 text-sm text-soft">
              <IconLock className="h-3.5 w-3.5" />
              {withheldText(r.blocked_count)}
            </p>
          )}
        </div>
      </div>
    );
  }
  return <p className="text-center text-sm text-soft">{m.text}</p>;
}

function Avatar() {
  return <Logo className="mt-0.5 h-7 w-7 shrink-0" />;
}

"use client";

import { useSyncExternalStore } from "react";
import { getUserId, onUserChange } from "../lib/session";
import type { AskResponse, Gap, Memory, UserId } from "../lib/types";

// Client-side app state: conversations (kept in this browser only) and the theme.

export type Mode = "interview" | "ask";

export type Message =
  | { id: string; role: "interviewer"; text: string; audio: string | null }
  | { id: string; role: "you"; text: string; saved?: Memory[] }
  | { id: string; role: "answer"; answer: AskResponse; question: string }
  | { id: string; role: "note"; text: string; gaps?: Gap[] };

export interface Conversation {
  id: string;
  mode: Mode;
  user: UserId;
  title: string;
  sessionId: string | null;
  messages: Message[];
  updatedAt: number;
}

interface State {
  conversations: Conversation[];
  activeId: string | null;
  mode: Mode;
}

const KEY = "handover_chats_v2";
let state: State = { conversations: [], activeId: null, mode: "interview" };
let loaded = false;
const listeners = new Set<() => void>();

// Switching viewer must never leave another viewer's chat open.
let watching = false;
function watchUser() {
  if (watching || typeof window === "undefined") return;
  watching = true;
  onUserChange(() => commit({ ...state, activeId: null }));
}

function load() {
  if (loaded || typeof window === "undefined") return;
  loaded = true;
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) state = { ...state, ...JSON.parse(raw), activeId: null };
  } catch {}
}

function commit(next: State) {
  state = next;
  try {
    localStorage.setItem(KEY, JSON.stringify({ conversations: state.conversations.slice(0, 40), mode: state.mode }));
  } catch {}
  listeners.forEach((l) => l());
}

const subscribe = (fn: () => void) => {
  load();
  watchUser();
  listeners.add(fn);
  return () => {
    listeners.delete(fn);
  };
};
const EMPTY: State = { conversations: [], activeId: null, mode: "interview" };

// Conversations live in this browser; each viewer only sees their own.
let view: { src: State; user: UserId; out: State } | null = null;
function ownView(): State {
  const user = getUserId();
  if (view && view.src === state && view.user === user) return view.out;
  const conversations = state.conversations.filter((c) => c.user === user);
  const activeId = conversations.some((c) => c.id === state.activeId) ? state.activeId : null;
  view = { src: state, user, out: { ...state, conversations, activeId } };
  return view.out;
}

export function useChats(): State {
  return useSyncExternalStore(subscribe, ownView, () => EMPTY);
}

export const uid = () => Math.random().toString(36).slice(2, 10);

export const chats = {
  get: ownView,
  setMode(mode: Mode) {
    commit({ ...state, mode, activeId: null });
  },
  newChat() {
    commit({ ...state, activeId: null });
  },
  open(id: string) {
    const c = state.conversations.find((x) => x.id === id);
    if (!c || c.user !== getUserId()) return;
    commit({ ...state, activeId: id, mode: c?.mode ?? state.mode });
  },
  create(c: Omit<Conversation, "id" | "updatedAt">): string {
    const id = uid();
    commit({ ...state, activeId: id, conversations: [{ ...c, id, updatedAt: Date.now() }, ...state.conversations] });
    return id;
  },
  update(id: string, fn: (c: Conversation) => Conversation) {
    commit({
      ...state,
      conversations: state.conversations.map((c) => (c.id === id ? { ...fn(c), updatedAt: Date.now() } : c)),
    });
  },
  remove(id: string) {
    commit({ ...state, activeId: state.activeId === id ? null : state.activeId, conversations: state.conversations.filter((c) => c.id !== id) });
  },
};

// ---------- theme ----------
export type Theme = "light" | "dark";
const themeListeners = new Set<() => void>();
function currentTheme(): Theme {
  return document.documentElement.dataset.theme === "dark" ? "dark" : "light";
}
export function useTheme(): Theme {
  return useSyncExternalStore(
    (fn) => {
      themeListeners.add(fn);
      return () => themeListeners.delete(fn);
    },
    currentTheme,
    () => "light",
  );
}
export function setTheme(t: Theme) {
  document.documentElement.dataset.theme = t;
  try {
    localStorage.setItem("handover_theme", t);
  } catch {}
  themeListeners.forEach((l) => l());
}


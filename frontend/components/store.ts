"use client";

import { useSyncExternalStore } from "react";
import type { AskResponse, Gap, Memory, UserId } from "../lib/types";

// Client-side app state: conversations (kept in this browser only) and the theme.

export type Mode = "interview" | "ask";

export type Message =
  | { id: string; role: "interviewer"; text: string; audio: string | null }
  | { id: string; role: "you"; text: string; saved?: Memory[] }
  | { id: string; role: "grandpa"; answer: AskResponse; question: string }
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

const KEY = "handover_chats_v1";
let state: State = { conversations: [], activeId: null, mode: "ask" };
let loaded = false;
const listeners = new Set<() => void>();

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
  listeners.add(fn);
  return () => {
    listeners.delete(fn);
  };
};
const EMPTY: State = { conversations: [], activeId: null, mode: "ask" };

export function useChats(): State {
  return useSyncExternalStore(subscribe, () => state, () => EMPTY);
}

export const uid = () => Math.random().toString(36).slice(2, 10);

export const chats = {
  get: () => state,
  setMode(mode: Mode) {
    commit({ ...state, mode, activeId: null });
  },
  newChat() {
    commit({ ...state, activeId: null });
  },
  open(id: string) {
    const c = state.conversations.find((x) => x.id === id);
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


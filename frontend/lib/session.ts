import type { UserId } from "./types";

// The current viewer. Module-level so the API client can log in as this viewer.
let current: UserId = "u_expert";
const listeners = new Set<() => void>();

export function getUserId(): UserId {
  return current;
}

export function setUserId(id: UserId) {
  current = id;
  try {
    localStorage.setItem("handover_user", id);
  } catch {}
  listeners.forEach((l) => l());
}

export function loadStoredUser() {
  try {
    const v = localStorage.getItem("handover_user");
    if (v === "u_expert" || v === "u_successor" || v === "u_outsider") setUserId(v);
  } catch {}
}

export function onUserChange(fn: () => void) {
  listeners.add(fn);
  return () => {
    listeners.delete(fn);
  };
}

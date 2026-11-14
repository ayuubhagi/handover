"use client";

import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";
import { api, errorMessage } from "./api";
import { getUserId, onUserChange } from "./session";
import type { LiveEvent, UserId } from "./types";

export function useUserId(): UserId {
  return useSyncExternalStore(onUserChange, getUserId, () => "u_expert" as UserId);
}

/** Load data for the current viewer; reloads when the viewer changes or `reload()` is called. */
export function useLoad<T>(fn: () => Promise<T>, deps: unknown[] = []) {
  const user = useUserId();
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const fnRef = useRef(fn);
  useEffect(() => {
    fnRef.current = fn;
  });
  const reload = useCallback(async () => {
    setLoading(true);
    try {
      setData(await fnRef.current());
      setError(null);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => {
    // Initial and viewer-change fetch; state updates happen after the await.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, reload, ...deps]);
  return { data, setData, error, loading, reload };
}

/** Subscribe to live events (WS /live, or the mock emitter). Reconnects when the viewer changes. */
export function useLive(onEvent: (e: LiveEvent) => void) {
  const user = useUserId();
  const [connected, setConnected] = useState(false);
  const ref = useRef(onEvent);
  useEffect(() => {
    ref.current = onEvent;
  });
  useEffect(() => api.subscribe((e) => ref.current(e), setConnected), [user]);
  return connected;
}

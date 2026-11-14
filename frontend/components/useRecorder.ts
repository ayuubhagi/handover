"use client";

import { useEffect, useRef, useState } from "react";
import { errorMessage } from "../lib/api";

/** MediaRecorder wrapper: start() asks for the mic, stop() resolves with the recorded blob. Exposes a live level 0..1. */
/** Hands-free end-of-turn: after speech is heard, this much quiet ends the turn. */
const SPEECH_LEVEL = 0.12;
const SILENCE_LEVEL = 0.06;
const SILENCE_MS = 1400;
const MAX_TURN_MS = 120_000;

export function useRecorder(opts?: { onSilence?: () => void }) {
  const onSilence = useRef(opts?.onSilence);
  useEffect(() => {
    onSilence.current = opts?.onSilence;
  });
  const [recording, setRecording] = useState(false);
  const [level, setLevel] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const rec = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);
  const resolver = useRef<((b: Blob | null) => void) | null>(null);
  const raf = useRef<number>(0);
  const ctx = useRef<AudioContext | null>(null);

  function cleanup() {
    cancelAnimationFrame(raf.current);
    ctx.current?.close().catch(() => {});
    ctx.current = null;
    rec.current?.stream.getTracks().forEach((t) => t.stop());
    rec.current = null;
    setLevel(0);
  }

  useEffect(() => () => cleanup(), []);

  async function start(): Promise<boolean> {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const r = new MediaRecorder(stream);
      chunks.current = [];
      r.ondataavailable = (e) => {
        if (e.data.size) chunks.current.push(e.data);
      };
      r.onstop = () => {
        const blob = chunks.current.length ? new Blob(chunks.current, { type: r.mimeType || "audio/webm" }) : null;
        cleanup();
        resolver.current?.(blob);
        resolver.current = null;
      };
      try {
        const ac = new AudioContext();
        const an = ac.createAnalyser();
        an.fftSize = 256;
        ac.createMediaStreamSource(stream).connect(an);
        ctx.current = ac;
        const buf = new Uint8Array(an.frequencyBinCount);
        const began = performance.now();
        let heard = false;
        let quietSince = 0;
        let fired = false;
        const tick = () => {
          an.getByteTimeDomainData(buf);
          let sum = 0;
          for (const v of buf) sum += ((v - 128) / 128) ** 2;
          const lvl = Math.min(1, Math.sqrt(sum / buf.length) * 4);
          setLevel(lvl);
          const now = performance.now();
          const live = stream.getAudioTracks().some((t) => t.enabled);
          if (live && lvl > SPEECH_LEVEL) {
            heard = true;
            quietSince = 0;
          } else if (heard && lvl < SILENCE_LEVEL) {
            quietSince ||= now;
          }
          if (!fired && ((heard && quietSince && now - quietSince > SILENCE_MS) || now - began > MAX_TURN_MS)) {
            fired = true;
            onSilence.current?.();
          }
          raf.current = requestAnimationFrame(tick);
        };
        tick();
      } catch {}
      r.start();
      rec.current = r;
      setRecording(true);
      return true;
    } catch (e) {
      setError(`Microphone unavailable: ${errorMessage(e)}`);
      return false;
    }
  }

  function stop(): Promise<Blob | null> {
    setRecording(false);
    if (!rec.current || rec.current.state === "inactive") return Promise.resolve(null);
    return new Promise((res) => {
      resolver.current = res;
      rec.current!.stop();
    });
  }

  function cancel() {
    resolver.current = null;
    if (rec.current && rec.current.state !== "inactive") {
      rec.current.onstop = () => cleanup();
      rec.current.stop();
    }
    setRecording(false);
  }

  function mute(on: boolean) {
    rec.current?.stream.getAudioTracks().forEach((t) => (t.enabled = !on));
  }

  return { recording, level, error, start, stop, cancel, mute };
}

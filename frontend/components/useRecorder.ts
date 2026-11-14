"use client";

import { useEffect, useRef, useState } from "react";
import { errorMessage } from "../lib/api";

/** MediaRecorder wrapper: start() asks for the mic, stop() resolves with the recorded blob. Exposes a live level 0..1. */
export function useRecorder() {
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
        const tick = () => {
          an.getByteTimeDomainData(buf);
          let sum = 0;
          for (const v of buf) sum += ((v - 128) / 128) ** 2;
          setLevel(Math.min(1, Math.sqrt(sum / buf.length) * 4));
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

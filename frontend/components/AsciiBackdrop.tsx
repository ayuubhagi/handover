"use client";

import { useEffect, useRef } from "react";

// Animated ASCII field. Pure characters on a grid: slow drifting waves pick the glyph
// and a moving hue band colours it (teal -> violet -> ember). No source image.

const RAMP = " .·:-=+*%#";
const CELL = 14;
const FPS = 30;

const PALETTE: [number, number, number][] = [
  [94, 214, 206], // teal
  [132, 140, 255], // violet
  [240, 122, 62], // ember
  [255, 196, 110], // amber
];

function mix(t: number): [number, number, number] {
  const x = ((t % 1) + 1) % 1 * PALETTE.length;
  const i = Math.floor(x);
  const f = x - i;
  const s = f * f * (3 - 2 * f);
  const a = PALETTE[i];
  const b = PALETTE[(i + 1) % PALETTE.length];
  return [a[0] + (b[0] - a[0]) * s, a[1] + (b[1] - a[1]) * s, a[2] + (b[2] - a[2]) * s];
}

export function AsciiBackdrop() {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let cols = 0;
    let rows = 0;
    let raf = 0;
    let last = 0;

    const size = () => {
      const w = window.innerWidth;
      const h = window.innerHeight;
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.font = `500 ${CELL - 2}px ui-monospace, "SF Mono", Menlo, Consolas, monospace`;
      ctx.textBaseline = "top";
      ctx.textAlign = "center";
      cols = Math.ceil(w / CELL) + 1;
      rows = Math.ceil(h / CELL) + 1;
    };

    const draw = (ms: number) => {
      const t = ms / 1000;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      for (let y = 0; y < rows; y++) {
        const v = y / rows;
        for (let x = 0; x < cols; x++) {
          const u = x / cols;
          // Three layered waves drifting in different directions.
          const w1 = Math.sin(u * 7.0 + t * 0.35 + Math.sin(v * 3.0 + t * 0.2) * 1.6);
          const w2 = Math.sin(v * 9.0 - t * 0.28 + Math.cos(u * 4.0 - t * 0.15) * 1.4);
          const w3 = Math.sin((u + v) * 5.0 + t * 0.22);
          const n = (w1 + w2 + w3) / 3; // -1..1
          const b = Math.max(0, n * 0.5 + 0.5 - 0.18) / 0.82;
          const idx = Math.floor(b * b * (RAMP.length - 1));
          if (idx <= 0) continue;
          const [r, g, bl] = mix(u * 0.55 + v * 0.35 + t * 0.03 + n * 0.08);
          ctx.fillStyle = `rgba(${r | 0},${g | 0},${bl | 0},${0.25 + b * 0.75})`;
          ctx.fillText(RAMP[idx], x * CELL + CELL / 2, y * CELL);
        }
      }
    };

    const loop = (ms: number) => {
      raf = requestAnimationFrame(loop);
      if (ms - last < 1000 / FPS) return;
      last = ms;
      draw(ms);
    };

    size();
    if (reduce) draw(0);
    else raf = requestAnimationFrame(loop);

    const onResize = () => {
      size();
      if (reduce) draw(0);
    };
    const onVis = () => {
      cancelAnimationFrame(raf);
      if (!document.hidden && !reduce) raf = requestAnimationFrame(loop);
    };
    window.addEventListener("resize", onResize);
    document.addEventListener("visibilitychange", onVis);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", onResize);
      document.removeEventListener("visibilitychange", onVis);
    };
  }, []);

  return (
    <div className="backdrop" aria-hidden="true">
      <canvas ref={ref} className="backdrop-ascii" />
      <div className="backdrop-vignette" />
    </div>
  );
}

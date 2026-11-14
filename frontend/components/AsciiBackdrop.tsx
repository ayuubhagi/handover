"use client";

import { useEffect, useRef } from "react";

// Faded ASCII figure behind the app: a head-and-shoulders silhouette smeared sideways,
// teal at the top fading to ember orange, drawn once per resize. Grain and vignette are CSS.

const RAMP = " .:+xX80S#@";
const CELL_W = 7;
const CELL_H = 12;

function hash(x: number, y: number) {
  const s = Math.sin(x * 127.1 + y * 311.7) * 43758.5453;
  return s - Math.floor(s);
}

function blob(x: number, y: number, cx: number, cy: number, rx: number, ry: number) {
  const dx = (x - cx) / rx;
  const dy = (y - cy) / ry;
  return Math.max(0, 1 - Math.sqrt(dx * dx + dy * dy));
}

function field(u: number, v: number) {
  // Silhouette sits right of centre so the chat column stays readable.
  const head = blob(u, v, 0.74, 0.25, 0.08, 0.13);
  const neck = blob(u, v, 0.76, 0.39, 0.05, 0.08) * 0.8;
  const body = blob(u, v, 0.8, 0.68, 0.22, 0.32) * 0.85;
  // Motion smear: sample the shape again further left, banded into horizontal streaks.
  const band = 0.55 + 0.45 * Math.sin(v * 140 + Math.sin(v * 23) * 3);
  const smear =
    Math.max(blob(u + 0.14, v, 0.74, 0.25, 0.14, 0.11), blob(u + 0.2, v, 0.82, 0.7, 0.32, 0.27)) * band * 0.75;
  return Math.min(1, Math.max(head, neck, body, smear));
}

function color(u: number, v: number, b: number) {
  // Teal (cool) up top and left, ember orange down and right.
  const t = Math.min(1, Math.max(0, v * 0.9 + (u - 0.5) * 0.7));
  const teal = [120, 214, 210];
  const ember = [255, 122, 58];
  const hot = [255, 236, 200];
  const c = teal.map((a, i) => a + (ember[i] - a) * t);
  const h = Math.max(0, b - 0.75) * 2.4;
  return `rgb(${c.map((a, i) => Math.round(a + (hot[i] - a) * h)).join(",")})`;
}

export function AsciiBackdrop() {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const draw = () => {
      const w = window.innerWidth;
      const h = window.innerHeight;
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, w, h);
      ctx.font = `600 ${CELL_H - 1}px ui-monospace, "SF Mono", Menlo, Consolas, monospace`;
      ctx.textBaseline = "top";
      const cols = Math.ceil(w / CELL_W);
      const rows = Math.ceil(h / CELL_H);
      const aspect = w / h;
      for (let y = 0; y < rows; y++) {
        for (let x = 0; x < cols; x++) {
          const u = 0.5 + ((x / cols - 0.5) * aspect) / 1.6;
          const v = y / rows;
          const n = hash(x, y);
          const b = field(u, v) * (0.75 + n * 0.4) - (n < 0.18 ? 0.25 : 0);
          if (b < 0.06) continue;
          const ch = RAMP[Math.min(RAMP.length - 1, Math.floor(b * RAMP.length))];
          if (ch === " ") continue;
          ctx.globalAlpha = Math.min(1, 0.45 + b);
          ctx.fillStyle = color(u, v, b);
          ctx.fillText(ch, x * CELL_W, y * CELL_H);
        }
      }
    };
    draw();
    let t: ReturnType<typeof setTimeout>;
    const onResize = () => {
      clearTimeout(t);
      t = setTimeout(draw, 120);
    };
    window.addEventListener("resize", onResize);
    return () => {
      clearTimeout(t);
      window.removeEventListener("resize", onResize);
    };
  }, []);

  return (
    <div className="backdrop" aria-hidden="true">
      <canvas ref={ref} className="backdrop-ascii" />
      <div className="backdrop-glow" />
      <div className="backdrop-grain" />
      <div className="backdrop-vignette" />
    </div>
  );
}

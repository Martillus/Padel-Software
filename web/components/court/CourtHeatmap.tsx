"use client";

import { useEffect, useRef } from "react";

import { drawCourtHeatmap } from "./drawCourt";

/** Mapa de calor de un jugador sobre la pista (10 x 20 m, proporción 1:2). */
export function CourtHeatmap({ cells, label, className = "" }: { cells: number[][] | null; label: string; className?: string }) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const draw = () => {
      const dpr = window.devicePixelRatio || 1;
      const w = canvas.clientWidth;
      const h = canvas.clientHeight;
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      drawCourtHeatmap(ctx, 0, 0, w, h, cells);
    };
    draw();
    const ro = new ResizeObserver(draw);
    ro.observe(canvas);
    return () => ro.disconnect();
  }, [cells]);

  return (
    <figure className={className}>
      <canvas ref={ref} role="img" aria-label={label} className="aspect-[1/2] w-full rounded-xl" />
      <figcaption className="mt-2 text-center text-xs text-muted">Arriba: campo lejano · Abajo: campo cercano a la cámara</figcaption>
    </figure>
  );
}

"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { applyH, COURT_LINES, homography, KEYPOINTS } from "@/lib/court";
import type { Calibration } from "@/lib/types";

import { CourtDiagram } from "../court/CourtDiagram";

type Pt = [number, number];

/**
 * El jugador marca puntos conocidos de la pista sobre un fotograma de su vídeo.
 * Con 4 o más puntos calculamos la perspectiva y dibujamos las líneas de la pista encima,
 * para que compruebe que encajan antes de enviar.
 */
export function CourtCalibrator({ file, onDone, onBack }: { file: File; onDone: (c: Calibration) => void; onBack: () => void }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const frameRef = useRef<HTMLCanvasElement | null>(null);
  const loupeRef = useRef<HTMLCanvasElement>(null);
  const [url] = useState(() => URL.createObjectURL(file));
  const [size, setSize] = useState<Pt | null>(null);
  const [time, setTime] = useState(0);
  const [loadError, setLoadError] = useState(false);
  const [points, setPoints] = useState<Record<string, Pt>>({});
  const [skipped, setSkipped] = useState<string[]>([]);
  const [order, setOrder] = useState<string[]>([]);
  const [drag, setDrag] = useState<{ id: string; pos: Pt } | null>(null);

  useEffect(() => () => URL.revokeObjectURL(url), [url]);

  const current = KEYPOINTS.find((k) => !(k.id in points) && !skipped.includes(k.id)) ?? null;
  const count = Object.keys(points).length;

  // Homografía pista -> imagen y error de los puntos marcados (para avisar de clics malos).
  const fit = useMemo(() => {
    const ids = Object.keys(points);
    if (ids.length < 4) return null;
    const court = ids.map((id) => KEYPOINTS.find((k) => k.id === id)!.court);
    const img = ids.map((id) => points[id]);
    const H = homography(court, img);
    if (!H) return null;
    const err = court.reduce((a, c, i) => {
      const [u, v] = applyH(H, c);
      return a + Math.hypot(u - img[i][0], v - img[i][1]);
    }, 0) / ids.length;
    return { H, err };
  }, [points]);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    const frame = frameRef.current;
    if (!canvas || !frame || !size) return;
    const ctx = canvas.getContext("2d")!;
    ctx.drawImage(frame, 0, 0);
    const s = size[0] / 1000; // escala de trazos según la resolución del vídeo
    if (fit) {
      ctx.strokeStyle = "rgba(200,241,53,.95)";
      ctx.lineWidth = 3 * s;
      for (const [a, b] of COURT_LINES) {
        const [x1, y1] = applyH(fit.H, a);
        const [x2, y2] = applyH(fit.H, b);
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();
      }
    }
    KEYPOINTS.forEach((k, i) => {
      const p = drag?.id === k.id ? drag.pos : points[k.id];
      if (!p) return;
      ctx.fillStyle = "#ef4444";
      ctx.strokeStyle = "#fff";
      ctx.lineWidth = 2.5 * s;
      ctx.beginPath();
      ctx.arc(p[0], p[1], 9 * s, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = "#fff";
      ctx.font = `bold ${14 * s}px system-ui, sans-serif`;
      ctx.fillText(String(i + 1), p[0] + 12 * s, p[1] - 10 * s);
    });
  }, [fit, points, drag, size]);

  useEffect(draw, [draw]);

  const grabFrame = useCallback(() => {
    const v = videoRef.current;
    if (!v || !v.videoWidth) return;
    const f = frameRef.current ?? document.createElement("canvas");
    f.width = v.videoWidth;
    f.height = v.videoHeight;
    f.getContext("2d")!.drawImage(v, 0, 0);
    frameRef.current = f;
    const c = canvasRef.current;
    if (c) {
      c.width = v.videoWidth;
      c.height = v.videoHeight;
    }
    setSize([v.videoWidth, v.videoHeight]);
    setTime(v.currentTime);
    requestAnimationFrame(draw);
  }, [draw]);

  const toImage = (e: React.PointerEvent): Pt => {
    const c = canvasRef.current!;
    const r = c.getBoundingClientRect();
    return [((e.clientX - r.left) * c.width) / r.width, ((e.clientY - r.top) * c.height) / r.height];
  };

  const showLoupe = (p: Pt) => {
    const l = loupeRef.current;
    const f = frameRef.current;
    if (!l || !f) return;
    const ctx = l.getContext("2d")!;
    const zoom = 3;
    const half = l.width / (2 * zoom);
    ctx.imageSmoothingEnabled = false;
    ctx.clearRect(0, 0, l.width, l.height);
    ctx.drawImage(f, p[0] - half, p[1] - half, half * 2, half * 2, 0, 0, l.width, l.height);
    ctx.strokeStyle = "#c8f135";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(l.width / 2, 0);
    ctx.lineTo(l.width / 2, l.height);
    ctx.moveTo(0, l.height / 2);
    ctx.lineTo(l.width, l.height / 2);
    ctx.stroke();
    l.style.visibility = "visible";
  };
  const hideLoupe = () => {
    if (loupeRef.current) loupeRef.current.style.visibility = "hidden";
  };

  const onDown = (e: React.PointerEvent) => {
    if (!size) return;
    const p = toImage(e);
    const r = canvasRef.current!.getBoundingClientRect();
    const tol = (24 * size[0]) / r.width;
    const near = Object.entries(points).find(([, q]) => Math.hypot(q[0] - p[0], q[1] - p[1]) < tol);
    const id = near?.[0] ?? current?.id;
    if (!id) return;
    (e.target as Element).setPointerCapture(e.pointerId);
    setDrag({ id, pos: p });
    showLoupe(p);
  };
  const onMove = (e: React.PointerEvent) => {
    if (!drag) return;
    const p = toImage(e);
    setDrag({ ...drag, pos: p });
    showLoupe(p);
  };
  const onUp = () => {
    if (!drag) return;
    setPoints((prev) => ({ ...prev, [drag.id]: drag.pos }));
    setOrder((o) => [...o.filter((x) => x !== drag.id), drag.id]);
    setDrag(null);
    hideLoupe();
  };

  const undo = () => {
    const last = order[order.length - 1];
    if (last) {
      setPoints(({ [last]: _gone, ...rest }) => rest);
      setOrder((o) => o.slice(0, -1));
    } else if (skipped.length) {
      setSkipped((s) => s.slice(0, -1));
    }
  };

  const nextFrame = () => {
    const v = videoRef.current;
    if (!v) return;
    v.currentTime = Math.min(v.duration - 0.1, v.currentTime + 4);
  };

  if (loadError) {
    return (
      <div className="card p-6">
        <h2 className="text-xl font-bold">Tu navegador no puede mostrar este vídeo</h2>
        <p className="mt-2 text-muted">
          Suele pasar con vídeos de iPhone en formato HEVC. Prueba a abrir esta página en Safari, o en el iPhone ve a
          Ajustes → Cámara → Formatos y elige «Más compatible» para tus próximas grabaciones.
        </p>
        <button className="btn-ghost mt-4" onClick={onBack}>Elegir otro vídeo</button>
      </div>
    );
  }

  return (
    <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_300px]">
      <div>
        <div className="relative overflow-hidden rounded-2xl border border-line bg-black">
          <video
            ref={videoRef}
            src={url}
            muted
            playsInline
            preload="auto"
            className="hidden"
            onLoadedMetadata={(e) => {
              const v = e.currentTarget;
              v.currentTime = Math.min(3, v.duration * 0.2);
            }}
            onSeeked={grabFrame}
            onError={() => setLoadError(true)}
          />
          {!size && <div className="flex aspect-video items-center justify-center text-muted">Cargando el vídeo…</div>}
          <canvas
            ref={canvasRef}
            className={`block w-full touch-none ${size ? "" : "hidden"} ${current || drag ? "cursor-crosshair" : "cursor-default"}`}
            onPointerDown={onDown}
            onPointerMove={onMove}
            onPointerUp={onUp}
            onPointerCancel={onUp}
            aria-label="Fotograma del vídeo: toca los puntos de la pista"
          />
          <canvas ref={loupeRef} width={160} height={160} className="pointer-events-none invisible absolute top-3 left-3 rounded-full border-2 border-ball shadow-2xl" />
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          <button className="btn-ghost text-sm" onClick={undo} disabled={!order.length && !skipped.length}>↶ Deshacer</button>
          <button className="btn-ghost text-sm" onClick={nextFrame}>Otro fotograma</button>
          <button className="btn-ghost text-sm" onClick={() => { setPoints({}); setSkipped([]); setOrder([]); }}>Empezar de nuevo</button>
        </div>
        <p className="mt-2 text-xs text-muted">Puedes arrastrar cualquier punto para afinarlo. Al tocar aparece una lupa.</p>
      </div>

      <div className="space-y-4">
        <div className="card p-4">
          <p className="text-xs font-semibold tracking-wide text-ball uppercase">
            Punto {Math.min(count + skipped.length + 1, KEYPOINTS.length)} de {KEYPOINTS.length} · marcados {count} (mínimo 4)
          </p>
          {current ? (
            <>
              <h3 className="mt-1 text-lg font-bold">{current.label}</h3>
              <p className="mt-1 text-sm text-muted">{current.hint}</p>
              <CourtDiagram className="mx-auto mt-3 block h-44" highlight={current.court} />
              <button className="btn-ghost mt-3 w-full text-sm" onClick={() => setSkipped((s) => [...s, current.id])}>
                No se ve, saltar
              </button>
            </>
          ) : (
            <p className="mt-2 text-sm text-muted">Has repasado todos los puntos. Revisa que las líneas encajan.</p>
          )}
        </div>

        {fit && (
          <div className={`rounded-2xl p-4 text-sm ${fit.err > size![0] * 0.012 ? "bg-amber-400/10 text-amber-200" : "bg-ball/10 text-ball"}`}>
            {fit.err > size![0] * 0.012
              ? "Algún punto parece mal colocado: las líneas verdes no encajan bien. Arrastra los puntos para corregirlo."
              : "¡Bien! Comprueba que las líneas verdes coinciden con las líneas de tu pista."}
          </div>
        )}

        <div className="flex gap-2">
          <button className="btn-ghost" onClick={onBack}>Atrás</button>
          <button
            className="btn-primary flex-1"
            disabled={!fit || !size}
            onClick={() => size && onDone({ frame_time_s: Number(time.toFixed(3)), frame_size: size, image_points: points })}
          >
            Continuar
          </button>
        </div>
      </div>
    </div>
  );
}

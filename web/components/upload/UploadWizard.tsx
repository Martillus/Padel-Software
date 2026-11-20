"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { formatPrice, MAX_VIDEO_MB, MAX_VIDEO_SECONDS, MIN_RECOMMENDED_SECONDS, PRICE_EUR, UPLOADS_ENABLED } from "@/lib/config";
import { addToHistory } from "@/lib/history";
import { formatDuration } from "@/lib/insights";
import type { Calibration } from "@/lib/types";

import { CourtCalibrator } from "./CourtCalibrator";
import { RecordingTips } from "./RecordingTips";

const STEPS = ["Cómo grabar", "Tu vídeo", "Marca la pista", "Detalles", "Enviar"];

interface VideoInfo {
  file: File;
  duration: number;
  width: number;
  height: number;
}

function readVideoInfo(file: File): Promise<VideoInfo> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const v = document.createElement("video");
    v.preload = "metadata";
    v.muted = true;
    v.onloadedmetadata = () => {
      resolve({ file, duration: v.duration, width: v.videoWidth, height: v.videoHeight });
      URL.revokeObjectURL(url);
    };
    v.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("formato"));
    };
    v.src = url;
  });
}

function uploadWithProgress(url: string, file: File, onProgress: (p: number) => void): Promise<void> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("PUT", url);
    xhr.setRequestHeader("Content-Type", file.type || "application/octet-stream");
    xhr.upload.onprogress = (e) => e.lengthComputable && onProgress(e.loaded / e.total);
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) return resolve();
      try {
        reject(new Error(JSON.parse(xhr.responseText).error));
      } catch {
        reject(new Error("No se ha podido subir el vídeo."));
      }
    };
    xhr.onerror = () => reject(new Error("Se ha cortado la conexión al subir el vídeo."));
    xhr.send(file);
  });
}

export function UploadWizard() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [video, setVideo] = useState<VideoInfo | null>(null);
  const [videoError, setVideoError] = useState<string | null>(null);
  const [calibration, setCalibration] = useState<Calibration | null>(null);
  const [sessionType, setSessionType] = useState<"partido" | "entrenamiento">("partido");
  const [players, setPlayers] = useState(4);
  const [email, setEmail] = useState("");
  const [consent, setConsent] = useState(false);
  const [progress, setProgress] = useState<number | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);

  async function pick(file: File | undefined) {
    setVideoError(null);
    if (!file) return;
    if (!file.type.startsWith("video/") && !/\.(mp4|mov|m4v|webm)$/i.test(file.name)) return setVideoError("Ese archivo no parece un vídeo.");
    if (file.size > MAX_VIDEO_MB * 1024 * 1024) return setVideoError(`El vídeo pesa más de ${MAX_VIDEO_MB / 1024} GB. Recórtalo o grábalo en 1080p.`);
    try {
      const info = await readVideoInfo(file);
      if (info.duration > MAX_VIDEO_SECONDS) return setVideoError("El vídeo dura más de 2 horas. Recórtalo antes de subirlo.");
      setVideo(info);
      setCalibration(null);
    } catch {
      setVideo({ file, duration: NaN, width: 0, height: 0 });
      setVideoError("Tu navegador no puede leer este vídeo. Si es de iPhone, prueba con Safari.");
    }
  }

  async function submit() {
    if (!video || !calibration) return;
    setSubmitError(null);
    setProgress(0);
    try {
      // 1) Crear el análisis. En producción, aquí iría antes el pago con Stripe.
      const ext = (/\.[a-z0-9]{2,4}$/i.exec(video.file.name)?.[0] ?? ".mp4").toLowerCase();
      const res = await fetch("/api/analisis", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ calibration, durationS: Number.isFinite(video.duration) ? video.duration : null, sessionType, players, email, consent, videoExt: ext }),
      });
      const body = await res.json();
      if (!res.ok) throw new Error(body.error ?? "No se ha podido crear el análisis.");
      const id: string = body.job.id;
      addToHistory({ id, createdAt: body.job.createdAt, title: `${sessionType === "partido" ? "Partido" : "Entrenamiento"} del ${new Date().toLocaleDateString("es-ES")}` });
      // 2) Subir el vídeo (en producción: directo a Cloudflare R2 con una URL firmada).
      await uploadWithProgress(`/api/analisis/${id}/video`, video.file, setProgress);
      router.push(`/analisis/${id}`);
    } catch (err) {
      setSubmitError((err as Error).message);
      setProgress(null);
    }
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:py-12">
      <ol className="mb-8 flex flex-wrap gap-2" aria-label="Pasos">
        {STEPS.map((s, i) => (
          <li
            key={s}
            className={`rounded-full px-3 py-1 text-xs font-semibold sm:text-sm ${
              i === step ? "bg-ball text-black" : i < step ? "bg-surface-2 text-ink" : "border border-line text-muted"
            }`}
            aria-current={i === step ? "step" : undefined}
          >
            {i + 1}. {s}
          </li>
        ))}
      </ol>

      {step === 0 && (
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl">Antes de grabar</h1>
          <p className="mt-2 max-w-2xl text-muted">Cuanto mejor se vea la pista, mejor será el análisis. Son 30 segundos de lectura.</p>
          <RecordingTips className="mt-6" />
          <div className="mt-8 flex gap-3">
            <button className="btn-primary" onClick={() => setStep(1)}>Ya tengo el vídeo</button>
          </div>
        </div>
      )}

      {step === 1 && (
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight">Sube tu vídeo</h1>
          <p className="mt-2 text-muted">Partido o entrenamiento, grabado con el móvil quieto detrás de la pista.</p>
          <label
            className={`mt-6 flex cursor-pointer flex-col items-center justify-center rounded-3xl border-2 border-dashed px-6 py-14 text-center transition ${
              dragOver ? "border-ball bg-ball/5" : "border-line hover:border-muted"
            }`}
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(false);
              void pick(e.dataTransfer.files[0]);
            }}
          >
            <span className="text-5xl" aria-hidden="true">🎬</span>
            <span className="mt-3 text-lg font-bold">Elige el vídeo o arrástralo aquí</span>
            <span className="mt-1 text-sm text-muted">MP4 o MOV · hasta {MAX_VIDEO_MB / 1024} GB · mejor de 10 a 90 minutos</span>
            <input type="file" accept="video/*" className="sr-only" onChange={(e) => void pick(e.target.files?.[0])} />
          </label>
          {videoError && <p className="mt-4 rounded-xl bg-red-500/10 px-4 py-3 text-sm text-red-200">{videoError}</p>}
          {video && !videoError && (
            <div className="card mt-4 flex flex-wrap items-center justify-between gap-3 p-4">
              <div>
                <p className="font-bold break-all">{video.file.name}</p>
                <p className="text-sm text-muted">
                  {formatDuration(video.duration)} · {(video.file.size / 1024 / 1024).toFixed(0)} MB · {video.width}×{video.height}
                </p>
                {video.duration < MIN_RECOMMENDED_SECONDS && (
                  <p className="mt-1 text-sm text-amber-200">Es un vídeo corto: verás las cifras, pero no habrá consejos (hacen falta 2 minutos de juego).</p>
                )}
                {video.height > video.width && <p className="mt-1 text-sm text-amber-200">Está en vertical. El análisis funciona mucho mejor grabando en horizontal.</p>}
              </div>
              <button className="btn-primary" onClick={() => setStep(2)}>Continuar</button>
            </div>
          )}
          <button className="btn-ghost mt-6" onClick={() => setStep(0)}>Atrás</button>
        </div>
      )}

      {step === 2 && video && (
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight">Marca la pista</h1>
          <p className="mt-2 mb-6 max-w-2xl text-muted">
            Toca en la imagen los puntos que te vamos pidiendo. Así la IA sabe medir en metros reales. Si un punto no se ve, sáltalo: con 4 basta.
          </p>
          <CourtCalibrator
            file={video.file}
            onBack={() => setStep(1)}
            onDone={(c) => {
              setCalibration(c);
              setStep(3);
            }}
          />
        </div>
      )}

      {step === 3 && (
        <div className="max-w-2xl">
          <h1 className="text-3xl font-extrabold tracking-tight">Unos detalles</h1>
          <div className="card mt-6 space-y-6 p-5">
            <fieldset>
              <legend className="font-semibold">¿Qué has grabado?</legend>
              <div className="mt-2 grid grid-cols-2 gap-2">
                {(["partido", "entrenamiento"] as const).map((t) => (
                  <button key={t} type="button" onClick={() => setSessionType(t)} aria-pressed={sessionType === t}
                    className={`rounded-xl border px-4 py-3 font-semibold capitalize ${sessionType === t ? "border-ball bg-ball/10 text-ball" : "border-line"}`}>
                    {t}
                  </button>
                ))}
              </div>
            </fieldset>
            <fieldset>
              <legend className="font-semibold">¿Cuántos jugadores hay en la pista?</legend>
              <div className="mt-2 grid grid-cols-4 gap-2">
                {[1, 2, 3, 4].map((n) => (
                  <button key={n} type="button" onClick={() => setPlayers(n)} aria-pressed={players === n}
                    className={`rounded-xl border px-4 py-3 font-bold ${players === n ? "border-ball bg-ball/10 text-ball" : "border-line"}`}>
                    {n}
                  </button>
                ))}
              </div>
            </fieldset>
            <label className="block">
              <span className="font-semibold">Tu email (opcional)</span>
              <span className="block text-sm text-muted">Te avisamos cuando el informe esté listo.</span>
              <input className="input mt-2" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="tu@email.com" autoComplete="email" />
            </label>
            <label className="flex items-start gap-3 text-sm">
              <input type="checkbox" className="mt-1 h-5 w-5 accent-[#c8f135]" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
              <span>
                Confirmo que <b>todas las personas que aparecen en el vídeo</b> han aceptado que se grabe y se analice, y acepto las{" "}
                <Link href="/condiciones" className="underline" target="_blank">condiciones</Link> y la{" "}
                <Link href="/privacidad" className="underline" target="_blank">política de privacidad</Link>.
              </span>
            </label>
          </div>
          <div className="mt-6 flex gap-3">
            <button className="btn-ghost" onClick={() => setStep(2)}>Atrás</button>
            <button className="btn-primary flex-1 sm:flex-none" disabled={!consent} onClick={() => setStep(4)}>Continuar</button>
          </div>
        </div>
      )}

      {step === 4 && video && calibration && (
        <div className="max-w-2xl">
          <h1 className="text-3xl font-extrabold tracking-tight">Todo listo</h1>
          <div className="card mt-6 divide-y divide-line">
            <div className="flex justify-between p-4"><span className="text-muted">Vídeo</span><span className="font-semibold">{formatDuration(video.duration)}</span></div>
            <div className="flex justify-between p-4"><span className="text-muted">Tipo</span><span className="font-semibold capitalize">{sessionType} · {players} jugadores</span></div>
            <div className="flex justify-between p-4"><span className="text-muted">Pista</span><span className="font-semibold">{Object.keys(calibration.image_points).length} puntos marcados</span></div>
            <div className="flex justify-between p-4 text-lg"><span>Total</span><span className="font-extrabold">{formatPrice(PRICE_EUR)}</span></div>
          </div>
          <p className="mt-3 rounded-xl bg-brand/10 px-4 py-3 text-sm text-blue-200">
            <b>Modo de pruebas:</b> todavía no se cobra. Cuando conectemos Stripe, este botón abrirá el pago con tarjeta, Apple Pay o Google Pay.
          </p>
          {!UPLOADS_ENABLED && (
            <p className="mt-3 rounded-xl bg-amber-400/10 px-4 py-3 text-sm text-amber-200">
              <b>Versión de prueba en internet:</b> todavía no se pueden analizar vídeos aquí (el motor de análisis aún no está en la nube).
              Mientras tanto, mira el <Link href="/analisis/demo" className="underline">partido de ejemplo</Link>.
            </p>
          )}
          {submitError && <p className="mt-4 rounded-xl bg-red-500/10 px-4 py-3 text-sm text-red-200">{submitError}</p>}
          {progress !== null ? (
            <div className="mt-6">
              <div className="flex justify-between text-sm"><span>Subiendo el vídeo…</span><span>{Math.round(progress * 100)}%</span></div>
              <div className="mt-2 h-3 overflow-hidden rounded-full bg-surface-2">
                <div className="h-full bg-ball transition-all" style={{ width: `${progress * 100}%` }} />
              </div>
              <p className="mt-2 text-xs text-muted">No cierres esta página hasta que termine la subida.</p>
            </div>
          ) : (
            <div className="mt-6 flex gap-3">
              <button className="btn-ghost" onClick={() => setStep(3)}>Atrás</button>
              <button className="btn-primary flex-1" onClick={submit} disabled={!UPLOADS_ENABLED}>Analizar mi partido · {formatPrice(PRICE_EUR)}</button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

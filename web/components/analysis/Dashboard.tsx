"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { addToHistory } from "@/lib/history";
import { formatDuration } from "@/lib/insights";
import type { AnalysisResponse, JobPublic } from "@/lib/types";

import { splitSections } from "../Markdown";
import { ChatPanel } from "./ChatPanel";
import { MatchSummary } from "./MatchSummary";
import { PlayerPicker } from "./PlayerPicker";
import { PlayerReport } from "./PlayerReport";

const STEPS: { key: JobPublic["status"][]; label: string }[] = [
  { key: ["esperando_video"], label: "Subiendo el vídeo" },
  { key: ["en_cola"], label: "En cola" },
  { key: ["procesando"], label: "Analizando el partido" },
  { key: ["listo"], label: "Informe listo" },
];

function Processing({ job }: { job: JobPublic }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);
  const current = STEPS.findIndex((s) => s.key.includes(job.status));
  const since = job.startedAt ? (now - new Date(job.startedAt).getTime()) / 1000 : 0;
  // Estimación en modo local (sin GPU): ~4 min de cálculo por minuto de vídeo.
  const estimate = job.durationS ? job.durationS * 4 : null;
  return (
    <div className="mx-auto max-w-xl px-4 py-16">
      <div className="card p-6 sm:p-8">
        <div className="mx-auto mb-6 h-14 w-14 animate-spin rounded-full border-4 border-surface-2 border-t-ball" aria-hidden="true" />
        <h1 className="text-center text-2xl font-extrabold">Estamos analizando tu partido</h1>
        <p className="mt-2 text-center text-muted">Puedes cerrar esta página: el análisis sigue y lo encontrarás en «Mis partidos».</p>
        <ol className="mt-8 space-y-3">
          {STEPS.map((s, i) => (
            <li key={s.label} className="flex items-center gap-3">
              <span
                className={`flex h-7 w-7 items-center justify-center rounded-full text-sm font-bold ${
                  i < current ? "bg-ball text-black" : i === current ? "bg-brand text-white" : "bg-surface-2 text-muted"
                }`}
              >
                {i < current ? "✓" : i + 1}
              </span>
              <span className={i === current ? "font-semibold" : "text-muted"}>{s.label}</span>
            </li>
          ))}
        </ol>
        {job.status === "procesando" && (
          <p className="mt-6 text-center text-sm text-muted">
            Llevamos {formatDuration(since)}
            {estimate ? ` · tiempo estimado: unos ${formatDuration(estimate)}` : ""}
          </p>
        )}
      </div>
    </div>
  );
}

export function Dashboard({ id }: { id: string }) {
  const [data, setData] = useState<AnalysisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [chatOpen, setChatOpen] = useState(false);

  const load = useCallback(async () => {
    try {
      const res = await fetch(`/api/analisis/${id}`, { cache: "no-store" });
      if (res.status === 404) return setError("No encontramos este análisis. Revisa el enlace.");
      if (!res.ok) throw new Error();
      setData((await res.json()) as AnalysisResponse);
    } catch {
      setError("No se ha podido cargar el análisis. Comprueba tu conexión.");
    }
  }, [id]);

  useEffect(() => {
    void load();
  }, [load]);

  const status = data?.job.status;
  useEffect(() => {
    if (!status || status === "listo" || status === "error") return;
    const t = setInterval(load, 4000);
    return () => clearInterval(t);
  }, [status, load]);

  useEffect(() => {
    if (data?.job && !data.job.demo) {
      addToHistory({ id, createdAt: data.job.createdAt, title: `${data.job.sessionType === "partido" ? "Partido" : "Entrenamiento"} del ${new Date(data.job.createdAt).toLocaleDateString("es-ES")}` });
    }
  }, [data?.job, id]);

  // Recordar el jugador elegido en el enlace (#J2) para poder compartirlo.
  useEffect(() => {
    const h = window.location.hash.slice(1);
    if (/^J\d$/.test(h)) setSelected(h);
  }, []);
  const choose = (pid: string) => {
    setSelected(pid);
    history.replaceState(null, "", `#${pid}`);
    setTimeout(() => document.getElementById("tu-informe")?.scrollIntoView({ behavior: "smooth", block: "start" }), 50);
  };

  if (error) {
    return (
      <div className="mx-auto max-w-xl px-4 py-20 text-center">
        <p className="text-lg">{error}</p>
        <Link href="/" className="btn-ghost mt-6">Volver al inicio</Link>
      </div>
    );
  }
  if (!data) return <div className="mx-auto max-w-xl px-4 py-24 text-center text-muted">Cargando…</div>;
  if (data.job.status === "error") {
    return (
      <div className="mx-auto max-w-xl px-4 py-20">
        <div className="card p-6 text-center">
          <h1 className="text-xl font-bold">No hemos podido analizar el vídeo</h1>
          <p className="mt-2 text-muted">{data.job.error}</p>
          <p className="mt-4 text-sm text-muted">Comprueba que la cámara estaba quieta y que marcaste bien la pista. Si el problema sigue, escríbenos.</p>
          <Link href="/subir" className="btn-primary mt-6">Probar con otro vídeo</Link>
        </div>
      </div>
    );
  }
  if (!data.analysis) return <Processing job={data.job} />;

  const analysis = data.analysis;
  const sections = data.reportMd ? splitSections(data.reportMd) : {};
  const withAI = !!analysis.informe?.generado_con_ia;
  const player = analysis.jugadores.find((p) => p.id === selected) ?? null;
  const photoUrl = analysis.foto_jugadores ? `/api/analisis/${id}/foto` : null;

  return (
    <div className="mx-auto max-w-6xl px-4 py-6 sm:py-10">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          {data.job.demo && <span className="mb-2 inline-block rounded-full bg-ball/15 px-3 py-1 text-xs font-bold text-ball">Partido de ejemplo</span>}
          <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl">Tu partido</h1>
          <p className="text-muted">
            {formatDuration(analysis.video.duracion_analizada_s)} analizados · {analysis.jugadores.length} jugadores ·{" "}
            {new Date(data.job.createdAt).toLocaleDateString("es-ES", { day: "numeric", month: "long", year: "numeric" })}
          </p>
        </div>
        <button onClick={() => setChatOpen(true)} className="btn-primary lg:hidden">💬 Pregunta a la IA</button>
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_380px]">
        <div className="space-y-6">
          <PlayerPicker analysis={analysis} photoUrl={photoUrl} selected={selected} onSelect={choose} />
          {player && (
            <PlayerReport analysis={analysis} player={player} aiText={withAI ? sections[player.id]?.trim() || null : null} onAsk={() => setChatOpen(true)} />
          )}
          <MatchSummary analysis={analysis} />
          <details className="card p-4 text-sm text-muted sm:p-6">
            <summary className="cursor-pointer font-semibold text-ink">Cómo se ha calculado y limitaciones</summary>
            <ul className="mt-3 list-disc space-y-1 pl-5">
              {analysis.limitaciones.map((l) => <li key={l}>{l}</li>)}
            </ul>
            <p className="mt-3">
              {withAI ? "Los textos del informe se han generado con inteligencia artificial." : "Informe automático generado a partir del vídeo."} Las cifras son estimaciones.
              No usamos reconocimiento facial: cada jugador se identifica por su posición en la pista.
            </p>
          </details>
        </div>

        {/* Chat: fijo a la derecha en escritorio, hoja deslizante en el móvil */}
        <aside className="hidden lg:block">
          <div className="card sticky top-20 h-[calc(100dvh-7rem)] overflow-hidden">
            <ChatPanel analysisId={id} focus={selected} />
          </div>
        </aside>
      </div>

      {chatOpen && (
        <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true" aria-label="Chat con la IA">
          <button className="absolute inset-0 bg-black/60" onClick={() => setChatOpen(false)} aria-label="Cerrar" />
          <div className="absolute inset-x-0 bottom-0 h-[85dvh] overflow-hidden rounded-t-3xl border-t border-line bg-surface">
            <ChatPanel analysisId={id} focus={selected} onClose={() => setChatOpen(false)} />
          </div>
        </div>
      )}
    </div>
  );
}

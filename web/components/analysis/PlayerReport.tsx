"use client";

import { useState } from "react";

import { computeBadges, fmt, kmh, placeLabel, playerColor } from "@/lib/insights";
import type { Analysis, Observation, PlayerStats } from "@/lib/types";

import { CourtHeatmap } from "../court/CourtHeatmap";
import { Markdown } from "../Markdown";
import { BadgeChip, Tile, ZoneBar } from "./Bits";
import { downloadShareImage } from "./shareImage";

const EXERCISES: Record<string, { nombre: string; descripcion: string }> = {
  subir_red: { nombre: "Globo + subida a la red", descripcion: "Golpea de fondo y sube a la red en 3 apoyos, terminando con una volea." },
  salir_transicion: { nombre: "Volea de transición y cierre", descripcion: "Desde la línea de saque, volea baja y dos pasos rápidos hacia la red. Series de 8 bolas." },
  pareja_alineada: { nombre: "Desplazamientos en pareja", descripcion: "Subid y bajad a la vez siguiendo la bola, como si os uniera una cuerda de 3 m." },
  defensa_fondo: { nombre: "Defensa de pared de fondo", descripcion: "Bolas a la pared de fondo: sal del cristal y devuelve con un globo profundo." },
  intensidad: { nombre: "Desplazamientos laterales", descripcion: "Series de 30 s de desplazamiento lateral con volea al final, descanso igual." },
};

function Observations({ items }: { items: Observation[] }) {
  const avisos = items.filter((o) => o.tipo === "aviso");
  const fuertes = items.filter((o) => o.tipo === "fortaleza");
  const mejoras = items.filter((o) => o.tipo === "mejora");
  const ejercicios = [...new Set(items.map((o) => o.ejercicio).filter((e): e is string => !!e && e in EXERCISES))];
  return (
    <div className="space-y-4 text-[15px] leading-relaxed">
      {avisos.map((o, i) => (
        <p key={i} className="rounded-xl bg-amber-400/10 px-3 py-2 text-sm text-amber-200">{o.texto}</p>
      ))}
      {fuertes.length > 0 && (
        <div>
          <h4 className="font-bold">Lo que haces bien</h4>
          <ul className="mt-1 list-disc space-y-1 pl-5">{fuertes.map((o, i) => <li key={i}>{o.texto}</li>)}</ul>
        </div>
      )}
      {mejoras.length > 0 && (
        <div>
          <h4 className="font-bold">Para mejorar</h4>
          <ul className="mt-1 list-disc space-y-1 pl-5">{mejoras.map((o, i) => <li key={i}>{o.texto}</li>)}</ul>
        </div>
      )}
      {ejercicios.length > 0 && (
        <div>
          <h4 className="font-bold">Ejercicios recomendados</h4>
          <ul className="mt-1 space-y-2">
            {ejercicios.map((e) => (
              <li key={e} className="rounded-xl bg-surface-2 px-3 py-2">
                <b>{EXERCISES[e].nombre}</b>
                <p className="text-sm text-muted">{EXERCISES[e].descripcion}</p>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export function PlayerReport({
  analysis,
  player,
  aiText,
  onAsk,
}: {
  analysis: Analysis;
  player: PlayerStats;
  aiText: string | null;
  onAsk: () => void;
}) {
  const [name, setName] = useState("");
  const [sharing, setSharing] = useState(false);
  const badges = computeBadges(analysis.jugadores)[player.id] ?? [];
  const color = playerColor(player.id);
  const cut = player.tiempo_cortado_pct ?? 0;

  return (
    <section id="tu-informe" className="card scroll-mt-20 overflow-hidden">
      <div className="h-1.5" style={{ background: color }} />
      <div className="p-4 sm:p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-sm font-semibold" style={{ color }}>Tu informe</p>
            <h2 className="text-2xl font-extrabold">{player.id}</h2>
            <p className="text-sm text-muted">{placeLabel(player)} · visible el {fmt(player.cobertura_pct)}% del partido</p>
          </div>
          <button onClick={onAsk} className="btn-ghost text-sm">💬 Pregúntale a la IA</button>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          {badges.map((b) => <BadgeChip key={b.title} badge={b} />)}
        </div>

        <div className="mt-5 grid grid-cols-2 gap-3 lg:grid-cols-4">
          <Tile value={`${fmt(player.distancia_m, 0)} m`} label="Distancia recorrida" />
          <Tile value={`${fmt(kmh(player.velocidad_punta_mps))} km/h`} label="Velocidad punta" />
          <Tile value={`${fmt(player.zonas_pct.red, 0)}%`} label="Tiempo en la red" />
          <Tile value={fmt(player.metros_por_minuto, 0)} label="Metros por minuto" hint="Metros recorridos por cada minuto de juego" />
        </div>

        <h3 className="mt-6 mb-2 font-bold">¿Dónde has jugado?</h3>
        <ZoneBar zones={player.zonas_pct} />

        <div className="mt-6 grid gap-6 sm:grid-cols-[200px_1fr]">
          <CourtHeatmap cells={player.mapa_calor_celdas} label={`Mapa de calor de ${player.id}`} className="mx-auto w-full max-w-[200px]" />
          <div>
            {aiText ? <Markdown text={aiText} className="text-[15px] leading-relaxed" /> : <Observations items={player.observaciones} />}
            {cut > 10 && (
              <p className="mt-3 rounded-xl bg-amber-400/10 px-3 py-2 text-sm text-amber-200">
                La cámara no veía el fondo de tu campo: el {fmt(cut, 0)}% del tiempo saliste cortado y ese recorrido no cuenta.
              </p>
            )}
          </div>
        </div>

        <div className="mt-6 rounded-2xl border border-line p-4">
          <h3 className="font-bold">Compártelo</h3>
          <p className="text-sm text-muted">Crea una imagen con tus números para Instagram o WhatsApp. Tu nombre no sale de tu móvil.</p>
          <div className="mt-3 flex flex-col gap-2 sm:flex-row">
            <input className="input" value={name} onChange={(e) => setName(e.target.value)} maxLength={24} placeholder="Tu nombre (opcional)" aria-label="Tu nombre para la imagen" />
            <button
              className="btn-primary whitespace-nowrap"
              disabled={sharing}
              onClick={async () => {
                setSharing(true);
                try {
                  await downloadShareImage(player, name.trim() || player.id, badges[0], color);
                } finally {
                  setSharing(false);
                }
              }}
            >
              {sharing ? "Creando…" : "Crear imagen"}
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}

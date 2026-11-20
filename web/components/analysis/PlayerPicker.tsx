"use client";

import { playerColor } from "@/lib/insights";
import type { Analysis } from "@/lib/types";

import { CourtDiagram } from "../court/CourtDiagram";

/** "¿Quién eres?": tocar la propia figura en la foto (o en el plano, si no hay foto). */
export function PlayerPicker({
  analysis,
  photoUrl,
  selected,
  onSelect,
}: {
  analysis: Analysis;
  photoUrl: string | null;
  selected: string | null;
  onSelect: (id: string) => void;
}) {
  const photo = analysis.foto_jugadores;
  return (
    <section className="card p-4 sm:p-6">
      <h2 className="text-xl font-bold">¿Quién eres?</h2>
      <p className="mt-1 text-sm text-muted">
        {photo && photoUrl ? "Toca tu figura en la foto para ver tu informe." : "Toca tu posición en la pista para ver tu informe."}
      </p>

      {photo && photoUrl ? (
        <div className="relative mt-4 overflow-hidden rounded-xl bg-black">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={photoUrl} alt="Foto del partido con los jugadores" className="block h-auto w-full" />
          {Object.entries(photo.cajas).map(([pid, [x1, y1, x2, y2]]) => {
            const pad = 0.25 * (x2 - x1);
            const active = selected === pid;
            return (
              <button
                key={pid}
                type="button"
                onClick={() => onSelect(pid)}
                aria-label={`Soy ${pid}`}
                className="absolute rounded-md border-[3px] transition"
                style={{
                  left: `${(100 * (x1 - pad)) / photo.ancho}%`,
                  top: `${(100 * y1) / photo.alto}%`,
                  width: `${(100 * (x2 - x1 + 2 * pad)) / photo.ancho}%`,
                  height: `${(100 * (y2 - y1)) / photo.alto}%`,
                  borderColor: playerColor(pid),
                  boxShadow: active ? `0 0 0 3px #fff, 0 0 22px ${playerColor(pid)}` : undefined,
                }}
              >
                <span className="absolute -top-6 left-1/2 -translate-x-1/2 rounded-full px-2 text-xs font-extrabold text-black" style={{ background: playerColor(pid) }}>
                  {pid}
                </span>
              </button>
            );
          })}
        </div>
      ) : (
        <CourtDiagram
          className="mx-auto mt-4 block max-h-[340px] w-full max-w-[220px]"
          points={analysis.jugadores.map((p) => ({ id: p.id, x: p.posicion_media.x, y: p.posicion_media.y, color: playerColor(p.id) }))}
          selected={selected}
          onSelect={onSelect}
        />
      )}

      <div className="mt-4 flex flex-wrap gap-2">
        {analysis.jugadores.map((p) => {
          const active = selected === p.id;
          return (
            <button
              key={p.id}
              type="button"
              onClick={() => onSelect(p.id)}
              className="rounded-full border-2 px-4 py-1.5 text-sm font-bold transition"
              style={{ borderColor: playerColor(p.id), background: active ? playerColor(p.id) : "transparent", color: active ? "#0b1220" : undefined }}
              aria-pressed={active}
            >
              {p.id}
            </button>
          );
        })}
      </div>
    </section>
  );
}

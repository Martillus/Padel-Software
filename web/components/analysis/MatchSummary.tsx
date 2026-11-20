import { computeBadges, fmt, formatDuration, kmh, playerColor } from "@/lib/insights";
import type { Analysis } from "@/lib/types";

import { BadgeChip, Tile } from "./Bits";

export function MatchSummary({ analysis }: { analysis: Analysis }) {
  const players = analysis.jugadores;
  const total = players.reduce((a, p) => a + p.distancia_m, 0);
  const fastest = players.reduce((a, p) => (p.velocidad_punta_mps > a.velocidad_punta_mps ? p : a), players[0]);
  const badges = computeBadges(players);
  const pairNotes = analysis.parejas.flatMap((q) => q.observaciones);

  return (
    <section className="card p-4 sm:p-6">
      <h2 className="text-xl font-bold">El partido</h2>
      <div className="mt-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Tile value={formatDuration(analysis.video.duracion_analizada_s)} label="Tiempo analizado" />
        <Tile value={`${fmt(total, 0)} m`} label="Metros entre todos" />
        <Tile value={fastest ? `${fmt(kmh(fastest.velocidad_punta_mps))} km/h` : "-"} label={`Punta más rápida${fastest ? ` (${fastest.id})` : ""}`} />
        <Tile value={String(players.length)} label="Jugadores" />
      </div>

      <h3 className="mt-6 mb-3 font-bold">Logros</h3>
      <div className="grid gap-2 sm:grid-cols-2">
        {players.flatMap((p) => (badges[p.id] ?? []).map((b) => <BadgeChip key={p.id + b.title} badge={b} who={p.id} whoColor={playerColor(p.id)} />))}
      </div>

      {analysis.parejas.length > 0 && (
        <>
          <h3 className="mt-6 mb-1 font-bold">Parejas</h3>
          <div className="divide-y divide-line">
            {analysis.parejas.map((q) => (
              <div key={q.jugadores.join()} className="flex flex-wrap items-center justify-between gap-3 py-3">
                <div>
                  <p className="font-bold">
                    {q.jugadores.map((id, i) => (
                      <span key={id}>
                        {i > 0 && " y "}
                        <i className="mr-1 inline-block h-2.5 w-2.5 rounded-full" style={{ background: playerColor(id) }} />
                        {id}
                      </span>
                    ))}
                  </p>
                  <p className="text-sm text-muted">Campo {q.campo === "cerca" ? "cercano" : "lejano"}</p>
                </div>
                <div className="flex gap-4 text-center text-sm">
                  <div><b className="block text-lg">{fmt(q.ambos_en_red_pct, 0)}%</b><span className="text-muted">juntos en la red</span></div>
                  <div><b className="block text-lg">{fmt(q.ambos_en_fondo_pct, 0)}%</b><span className="text-muted">juntos al fondo</span></div>
                  <div><b className="block text-lg">{fmt(q.desalineados_pct, 0)}%</b><span className="text-muted">desalineados</span></div>
                </div>
              </div>
            ))}
          </div>
          {pairNotes.length > 0 && (
            <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-muted">{pairNotes.map((o, i) => <li key={i}>{o.texto}</li>)}</ul>
          )}
        </>
      )}
    </section>
  );
}

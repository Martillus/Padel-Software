// Logros y utilidades de presentación (mismas reglas que engine/padel_engine/report_html.py).
import type { PlayerStats } from "./types";

export const PLAYER_COLORS: Record<string, string> = {
  J1: "#facc15",
  J2: "#f87171",
  J3: "#4ade80",
  J4: "#c084fc",
  J5: "#f8fafc",
  J6: "#22d3ee",
};

export const playerColor = (id: string) => PLAYER_COLORS[id] ?? "#e2e8f0";

export interface Badge {
  icon: string;
  title: string;
  description: string;
}

/** Logros del partido comparando a los jugadores entre sí (nombres neutros). */
export function computeBadges(players: PlayerStats[]): Record<string, Badge[]> {
  const out: Record<string, Badge[]> = Object.fromEntries(players.map((p) => [p.id, []]));
  if (!players.length) return out;
  const award = (key: (p: PlayerStats) => number, badge: Badge, min?: number) => {
    const best = players.reduce((a, b) => (key(b) > key(a) ? b : a));
    if (min === undefined || key(best) >= min) out[best.id].push(badge);
  };
  award((p) => p.distancia_m, { icon: "🏃", title: "Más metros recorridos", description: "Quien más ha corrido del partido" });
  award((p) => p.zonas_pct.red, { icon: "🎾", title: "Dominio de la red", description: "Más tiempo jugando en la red" }, 25);
  award((p) => p.zonas_pct.fondo, { icon: "🧱", title: "Muro del fondo", description: "Más tiempo defendiendo desde el fondo" }, 40);
  award((p) => p.velocidad_punta_mps, { icon: "⚡", title: "Máxima velocidad", description: "El desplazamiento más rápido del partido" });
  for (const p of players) {
    if (out[p.id].length) continue;
    const balanced = Math.max(p.zonas_pct.red, p.zonas_pct.transicion, p.zonas_pct.fondo) < 50;
    out[p.id].push(
      balanced
        ? { icon: "🔄", title: "Todoterreno", description: "Juega repartido entre red, transición y fondo" }
        : { icon: "🎯", title: "Constancia", description: "Presente en todo el partido" },
    );
  }
  return out;
}

export const fmt = (n: number, digits = 1) => n.toLocaleString("es-ES", { maximumFractionDigits: digits });
export const kmh = (mps: number) => mps * 3.6;

export function formatDuration(s: number): string {
  if (s < 60) return `${Math.round(s)} s`;
  const m = Math.floor(s / 60);
  const r = Math.round(s % 60);
  return r ? `${m} min ${r} s` : `${m} min`;
}

export const placeLabel = (p: PlayerStats) =>
  `Campo ${p.campo === "cerca" ? "cercano a la cámara" : "lejano"}, lado ${p.lado_habitual}`;

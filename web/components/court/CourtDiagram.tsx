import { COURT_L, COURT_LINES, COURT_W } from "@/lib/court";

export interface DiagramPoint {
  id: string;
  x: number;
  y: number;
  color: string;
}

/**
 * Plano de la pista visto desde la cámara (campo lejano arriba) con puntos tocables.
 * Se usa para elegir jugador cuando no hay foto, y para ilustrar puntos de calibración.
 */
export function CourtDiagram({
  points = [],
  selected,
  onSelect,
  highlight,
  className = "",
}: {
  points?: DiagramPoint[];
  selected?: string | null;
  onSelect?: (id: string) => void;
  highlight?: [number, number] | null;
  className?: string;
}) {
  const pad = 1.2;
  const vb = `${-pad} ${-pad} ${COURT_W + 2 * pad} ${COURT_L + 2 * pad}`;
  const Y = (y: number) => COURT_L - y;
  return (
    <svg viewBox={vb} className={className} role="img" aria-label="Plano de la pista">
      <rect x={-pad} y={-pad} width={COURT_W + 2 * pad} height={COURT_L + 2 * pad} rx={0.8} fill="#0d1a33" />
      <rect x={0} y={0} width={COURT_W} height={COURT_L} fill="#2563c9" />
      {COURT_LINES.map(([[x1, y1], [x2, y2]], i) => (
        <line key={i} x1={x1} y1={Y(y1)} x2={x2} y2={Y(y2)} stroke="#fff" strokeWidth={y1 === 10 && y2 === 10 ? 0.18 : 0.08} strokeLinecap="round" />
      ))}
      <text x={COURT_W / 2} y={COURT_L + 0.95} textAnchor="middle" fontSize={0.6} fill="#93a1bd">
        cámara
      </text>
      {highlight && (
        <g>
          <circle cx={highlight[0]} cy={Y(highlight[1])} r={0.9} fill="none" stroke="#c8f135" strokeWidth={0.18}>
            <animate attributeName="r" values="0.5;1.1;0.5" dur="1.4s" repeatCount="indefinite" />
          </circle>
          <circle cx={highlight[0]} cy={Y(highlight[1])} r={0.28} fill="#c8f135" />
        </g>
      )}
      {points.map((p) => {
        const active = selected === p.id;
        const content = (
          <g>
            <circle cx={p.x} cy={Y(p.y)} r={active ? 1.05 : 0.85} fill={p.color} stroke={active ? "#fff" : "#0b1220"} strokeWidth={active ? 0.22 : 0.12} />
            <text x={p.x} y={Y(p.y) + 0.3} textAnchor="middle" fontSize={0.8} fontWeight={800} fill="#0b1220">
              {p.id}
            </text>
          </g>
        );
        return onSelect ? (
          <g key={p.id} role="button" tabIndex={0} aria-label={`Soy ${p.id}`} className="cursor-pointer outline-none"
            onClick={() => onSelect(p.id)}
            onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && onSelect(p.id)}>
            <circle cx={p.x} cy={Y(p.y)} r={1.6} fill="transparent" />
            {content}
          </g>
        ) : (
          <g key={p.id}>{content}</g>
        );
      })}
    </svg>
  );
}

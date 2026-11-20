import type { Badge } from "@/lib/insights";
import { fmt } from "@/lib/insights";
import type { Zone } from "@/lib/types";

export function Tile({ value, label, hint }: { value: string; label: string; hint?: string }) {
  return (
    <div className="rounded-2xl bg-surface-2 p-4" title={hint}>
      <div className="text-2xl font-extrabold tabular-nums leading-none sm:text-[28px]">{value}</div>
      <div className="mt-2 text-xs text-muted sm:text-sm">{label}</div>
    </div>
  );
}

const ZONES: { key: Zone; label: string; cls: string }[] = [
  { key: "red", label: "Red", cls: "bg-zone-red" },
  { key: "transicion", label: "Transición", cls: "bg-zone-trans" },
  { key: "fondo", label: "Fondo", cls: "bg-zone-fondo" },
];

export function ZoneBar({ zones }: { zones: Record<Zone, number> }) {
  return (
    <div>
      <div className="flex h-4 overflow-hidden rounded-full bg-surface-2" role="img" aria-label={ZONES.map((z) => `${z.label} ${fmt(zones[z.key], 0)}%`).join(", ")}>
        {ZONES.map((z) => (
          <div key={z.key} className={z.cls} style={{ width: `${zones[z.key]}%` }} />
        ))}
      </div>
      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted">
        {ZONES.map((z) => (
          <span key={z.key} className="inline-flex items-center gap-1.5">
            <i className={`inline-block h-2.5 w-2.5 rounded-sm ${z.cls}`} />
            {z.label} <b className="text-ink">{fmt(zones[z.key], 0)}%</b>
          </span>
        ))}
      </div>
    </div>
  );
}

export function BadgeChip({ badge, who, whoColor }: { badge: Badge; who?: string; whoColor?: string }) {
  return (
    <div className="flex items-center gap-3 rounded-2xl bg-surface-2 px-3.5 py-2.5">
      <span className="text-2xl" aria-hidden="true">{badge.icon}</span>
      <div>
        <p className="text-sm font-bold">
          {badge.title}
          {who && (
            <span className="ml-2 inline-flex items-center gap-1 text-xs text-muted">
              <i className="inline-block h-2 w-2 rounded-full" style={{ background: whoColor }} />
              {who}
            </span>
          )}
        </p>
        <p className="text-xs text-muted">{badge.description}</p>
      </div>
    </div>
  );
}

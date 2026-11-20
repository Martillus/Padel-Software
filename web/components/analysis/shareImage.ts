// Imagen para compartir en redes (1080 x 1350). Se dibuja en el navegador: el nombre que
// escribe el jugador no sale de su dispositivo.
import { APP_NAME } from "@/lib/config";
import { fmt, kmh, type Badge } from "@/lib/insights";
import type { PlayerStats } from "@/lib/types";

import { drawCourtHeatmap } from "../court/drawCourt";

function rrect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

export async function downloadShareImage(p: PlayerStats, name: string, badge: Badge | undefined, color: string): Promise<void> {
  const W = 1080;
  const H = 1350;
  const canvas = document.createElement("canvas");
  canvas.width = W;
  canvas.height = H;
  const ctx = canvas.getContext("2d")!;
  const font = (weight: number, size: number) => `${weight} ${size}px Inter, system-ui, -apple-system, sans-serif`;

  const g = ctx.createLinearGradient(0, 0, W, H);
  g.addColorStop(0, "#0f2a66");
  g.addColorStop(1, "#050a16");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, W, H);

  ctx.fillStyle = "#c8f135";
  ctx.font = font(700, 32);
  ctx.fillText("MI PARTIDO DE PÁDEL", 72, 118);
  ctx.fillStyle = "#ffffff";
  ctx.font = font(800, 98);
  ctx.fillText(name, 72, 228, W - 144);
  ctx.fillStyle = color;
  ctx.fillRect(72, 256, 150, 10);

  if (badge) {
    ctx.fillStyle = "rgba(255,255,255,.1)";
    rrect(ctx, 72, 304, W - 144, 100, 50);
    ctx.fill();
    ctx.fillStyle = "#fff";
    ctx.font = font(700, 44);
    ctx.fillText(`${badge.icon}  ${badge.title}`, 112, 371, W - 230);
  }

  const stats: [string, string][] = [
    [`${fmt(p.distancia_m, 0)} m`, "recorridos"],
    [`${fmt(kmh(p.velocidad_punta_mps))} km/h`, "velocidad punta"],
    [`${fmt(p.zonas_pct.red, 0)}%`, "en la red"],
    [fmt(p.metros_por_minuto, 0), "metros por minuto"],
  ];
  stats.forEach(([v, l], i) => {
    const y = 520 + i * 190;
    ctx.fillStyle = "#fff";
    ctx.font = font(800, 84);
    ctx.fillText(v, 72, y, 560);
    ctx.fillStyle = "rgba(255,255,255,.65)";
    ctx.font = font(500, 36);
    ctx.fillText(l, 72, y + 52);
  });

  const mw = 360;
  const mh = 720;
  ctx.save();
  rrect(ctx, W - 72 - mw, 460, mw, mh, 28);
  ctx.clip();
  drawCourtHeatmap(ctx, W - 72 - mw, 460, mw, mh, p.mapa_calor_celdas);
  ctx.restore();

  ctx.fillStyle = "rgba(255,255,255,.55)";
  ctx.font = font(500, 30);
  ctx.fillText(`${APP_NAME} · análisis con IA`, 72, H - 64);

  const blob: Blob | null = await new Promise((r) => canvas.toBlob(r, "image/png"));
  if (!blob) return;
  const file = new File([blob], `mi-partido-${p.id}.png`, { type: "image/png" });
  // En el móvil, abre el menú de compartir (Instagram, WhatsApp...) si está disponible.
  const nav = navigator as Navigator & { canShare?: (d: { files: File[] }) => boolean };
  if (nav.canShare?.({ files: [file] })) {
    try {
      await nav.share({ files: [file], title: "Mi partido de pádel" });
      return;
    } catch {
      /* el usuario canceló: descargamos */
    }
  }
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = file.name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}

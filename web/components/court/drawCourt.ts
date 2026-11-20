// Dibujo de la pista y del mapa de calor en un <canvas>. Lo usan el mapa de calor y la
// imagen para compartir. Vista desde la cámara: campo lejano arriba, cercano abajo.
import { COURT_L, COURT_LINES, COURT_W } from "@/lib/court";

// Rampa de color tipo "inferno" (oscuro -> amarillo).
const RAMP: [number, number, number][] = [
  [20, 11, 52],
  [120, 28, 109],
  [196, 58, 77],
  [244, 120, 31],
  [252, 210, 64],
  [252, 255, 164],
];

function rampColor(t: number): [number, number, number] {
  const x = Math.min(1, Math.max(0, t)) * (RAMP.length - 1);
  const i = Math.min(RAMP.length - 2, Math.floor(x));
  const f = x - i;
  return [0, 1, 2].map((k) => Math.round(RAMP[i][k] + (RAMP[i + 1][k] - RAMP[i][k]) * f)) as [number, number, number];
}

/** Amplía la rejilla (factor) y la suaviza con un filtro gaussiano para que no se vea pixelada. */
function smoothHeat(cells: number[][], factor: number, sigma: number): { w: number; h: number; data: Float32Array } {
  const rows = cells.length;
  const cols = cells[0].length;
  const w = cols * factor;
  const h = rows * factor;
  const src = new Float32Array(w * h);
  for (let r = 0; r < h; r++) for (let c = 0; c < w; c++) src[r * w + c] = cells[Math.floor(r / factor)][Math.floor(c / factor)];
  const rad = Math.ceil(sigma * 3);
  const k = Array.from({ length: 2 * rad + 1 }, (_, i) => Math.exp(-((i - rad) ** 2) / (2 * sigma * sigma)));
  const ks = k.reduce((a, b) => a + b, 0);
  const tmp = new Float32Array(w * h);
  const out = new Float32Array(w * h);
  for (let r = 0; r < h; r++)
    for (let c = 0; c < w; c++) {
      let acc = 0;
      for (let i = -rad; i <= rad; i++) acc += src[r * w + Math.min(w - 1, Math.max(0, c + i))] * k[i + rad];
      tmp[r * w + c] = acc / ks;
    }
  for (let r = 0; r < h; r++)
    for (let c = 0; c < w; c++) {
      let acc = 0;
      for (let i = -rad; i <= rad; i++) acc += tmp[Math.min(h - 1, Math.max(0, r + i)) * w + c] * k[i + rad];
      out[r * w + c] = acc / ks;
    }
  return { w, h, data: out };
}

/** Dibuja la pista con el mapa de calor en el rectángulo (x, y, w, h) del contexto. */
export function drawCourtHeatmap(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  cells: number[][] | null,
): void {
  ctx.save();
  ctx.fillStyle = "#2563c9";
  ctx.fillRect(x, y, w, h);

  if (cells && cells.length) {
    const heat = smoothHeat(cells, 4, 3.2);
    const max = Math.max(...heat.data, 1e-9);
    const small = document.createElement("canvas");
    small.width = heat.w;
    small.height = heat.h;
    const sctx = small.getContext("2d")!;
    const img = sctx.createImageData(heat.w, heat.h);
    for (let r = 0; r < heat.h; r++) {
      for (let c = 0; c < heat.w; c++) {
        const v = Math.pow(heat.data[r * heat.w + c] / max, 0.65);
        const [R, G, B] = rampColor(v);
        // Fila 0 = fondo cercano -> abajo del todo en el dibujo.
        const o = ((heat.h - 1 - r) * heat.w + c) * 4;
        img.data[o] = R;
        img.data[o + 1] = G;
        img.data[o + 2] = B;
        img.data[o + 3] = v < 0.04 ? 0 : Math.round(Math.min(1, v * 1.2) * 230);
      }
    }
    sctx.putImageData(img, 0, 0);
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = "high";
    ctx.drawImage(small, x, y, w, h);
  }

  ctx.strokeStyle = "rgba(255,255,255,.92)";
  ctx.lineCap = "round";
  const sx = w / COURT_W;
  const sy = h / COURT_L;
  for (const [[x1, y1], [x2, y2]] of COURT_LINES) {
    ctx.lineWidth = y1 === 10 && y2 === 10 ? Math.max(2, w * 0.018) : Math.max(1, w * 0.009);
    ctx.beginPath();
    ctx.moveTo(x + x1 * sx, y + h - y1 * sy);
    ctx.lineTo(x + x2 * sx, y + h - y2 * sy);
    ctx.stroke();
  }
  ctx.restore();
}

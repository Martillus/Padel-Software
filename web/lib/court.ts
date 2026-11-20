// Geometría de la pista (igual que engine/padel_engine/court.py).
// Metros; la cámara está detrás de la pista: y = 0 fondo cercano, y = 20 fondo lejano.

export const COURT_W = 10;
export const COURT_L = 20;
export const NET_Y = 10;
export const NEAR_SERVICE_Y = 3.05;
export const FAR_SERVICE_Y = 16.95;

export const COURT_LINES: [[number, number], [number, number]][] = [
  [[0, 0], [COURT_W, 0]],
  [[0, COURT_L], [COURT_W, COURT_L]],
  [[0, 0], [0, COURT_L]],
  [[COURT_W, 0], [COURT_W, COURT_L]],
  [[0, NET_Y], [COURT_W, NET_Y]],
  [[0, NEAR_SERVICE_Y], [COURT_W, NEAR_SERVICE_Y]],
  [[0, FAR_SERVICE_Y], [COURT_W, FAR_SERVICE_Y]],
  [[COURT_W / 2, NEAR_SERVICE_Y], [COURT_W / 2, FAR_SERVICE_Y]],
];

export interface Keypoint {
  id: string;
  court: [number, number];
  label: string;
  hint: string;
}

/** Orden en que pedimos marcar los puntos (primero los que mejor se ven desde detrás). */
export const KEYPOINTS: Keypoint[] = [
  { id: "far_left", court: [0, COURT_L], label: "Esquina del fondo lejano, izquierda", hint: "Donde el cristal del fondo lejano toca el suelo, a la izquierda." },
  { id: "far_right", court: [COURT_W, COURT_L], label: "Esquina del fondo lejano, derecha", hint: "Donde el cristal del fondo lejano toca el suelo, a la derecha." },
  { id: "net_left", court: [0, NET_Y], label: "Poste de la red, izquierda", hint: "La base del poste izquierdo de la red, en el suelo." },
  { id: "net_right", court: [COURT_W, NET_Y], label: "Poste de la red, derecha", hint: "La base del poste derecho de la red, en el suelo." },
  { id: "far_service_center", court: [COURT_W / 2, FAR_SERVICE_Y], label: "T del campo lejano", hint: "Donde la línea central se une con la línea de saque del campo lejano." },
  { id: "near_service_left", court: [0, NEAR_SERVICE_Y], label: "Línea de saque cercana, izquierda", hint: "Donde la línea de saque de tu lado toca el cristal izquierdo." },
  { id: "near_service_right", court: [COURT_W, NEAR_SERVICE_Y], label: "Línea de saque cercana, derecha", hint: "Donde la línea de saque de tu lado toca el cristal derecho." },
  { id: "near_service_center", court: [COURT_W / 2, NEAR_SERVICE_Y], label: "T del campo cercano", hint: "Donde la línea central se une con la línea de saque de tu lado." },
];

export function zoneOf(y: number): "red" | "transicion" | "fondo" {
  const d = Math.abs(y - NET_Y);
  if (d <= 3.5) return "red";
  if (d <= 6.95) return "transicion";
  return "fondo";
}

// --- Homografía (pista -> imagen) para dibujar las líneas sobre el fotograma ----------

type Mat3 = number[]; // fila a fila, 9 valores

function solve(A: number[][], b: number[]): number[] | null {
  const n = b.length;
  const M = A.map((row, i) => [...row, b[i]]);
  for (let c = 0; c < n; c++) {
    let p = c;
    for (let r = c + 1; r < n; r++) if (Math.abs(M[r][c]) > Math.abs(M[p][c])) p = r;
    if (Math.abs(M[p][c]) < 1e-12) return null;
    [M[c], M[p]] = [M[p], M[c]];
    for (let r = 0; r < n; r++) {
      if (r === c) continue;
      const f = M[r][c] / M[c][c];
      for (let k = c; k <= n; k++) M[r][k] -= f * M[c][k];
    }
  }
  return M.map((row, i) => row[n] / row[i]);
}

/** Homografía por mínimos cuadrados (h33 = 1) a partir de 4 o más parejas de puntos. */
export function homography(src: [number, number][], dst: [number, number][]): Mat3 | null {
  if (src.length < 4) return null;
  const AtA = Array.from({ length: 8 }, () => new Array(8).fill(0));
  const Atb = new Array(8).fill(0);
  const add = (row: number[], v: number) => {
    for (let i = 0; i < 8; i++) {
      Atb[i] += row[i] * v;
      for (let j = 0; j < 8; j++) AtA[i][j] += row[i] * row[j];
    }
  };
  src.forEach(([x, y], i) => {
    const [u, v] = dst[i];
    add([x, y, 1, 0, 0, 0, -u * x, -u * y], u);
    add([0, 0, 0, x, y, 1, -v * x, -v * y], v);
  });
  const h = solve(AtA, Atb);
  return h ? [...h, 1] : null;
}

export function applyH(H: Mat3, [x, y]: [number, number]): [number, number] {
  const w = H[6] * x + H[7] * y + H[8];
  return [(H[0] * x + H[1] * y + H[2]) / w, (H[3] * x + H[4] * y + H[5]) / w];
}

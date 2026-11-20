import { NextResponse } from "next/server";

import { MAX_VIDEO_SECONDS, UPLOADS_ENABLED } from "@/lib/config";
import { KEYPOINTS } from "@/lib/court";
import { createJob } from "@/lib/jobs";
import type { Calibration } from "@/lib/types";

const VALID_POINTS = new Set(KEYPOINTS.map((k) => k.id));

/** Crea un análisis (todavía sin vídeo). En producción, aquí se comprueba antes el pago. */
export async function POST(req: Request) {
  if (!UPLOADS_ENABLED) {
    return NextResponse.json({ error: "En esta versión de prueba todavía no se pueden analizar vídeos." }, { status: 503 });
  }
  let body: Record<string, unknown>;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Petición no válida." }, { status: 400 });
  }
  const cal = body.calibration as Calibration | undefined;
  const points = cal?.image_points ?? {};
  const names = Object.keys(points);
  if (!cal || names.length < 4 || names.some((n) => !VALID_POINTS.has(n))) {
    return NextResponse.json({ error: "Marca al menos 4 puntos de la pista." }, { status: 400 });
  }
  const ok = (v: unknown) => typeof v === "number" && Number.isFinite(v);
  if (!names.every((n) => Array.isArray(points[n]) && ok(points[n][0]) && ok(points[n][1])) || !ok(cal.frame_time_s)) {
    return NextResponse.json({ error: "Calibración no válida." }, { status: 400 });
  }
  if (!Array.isArray(cal.frame_size) || !ok(cal.frame_size[0]) || !ok(cal.frame_size[1])) {
    return NextResponse.json({ error: "Falta el tamaño del vídeo." }, { status: 400 });
  }
  if (body.consent !== true) {
    return NextResponse.json({ error: "Hace falta aceptar las condiciones." }, { status: 400 });
  }
  const durationS = ok(body.durationS) ? (body.durationS as number) : null;
  if (durationS !== null && durationS > MAX_VIDEO_SECONDS) {
    return NextResponse.json({ error: "El vídeo es demasiado largo (máximo 2 horas)." }, { status: 400 });
  }
  const ext = typeof body.videoExt === "string" && /^\.[a-z0-9]{2,4}$/i.test(body.videoExt) ? body.videoExt.toLowerCase() : ".mp4";
  const players = Math.min(4, Math.max(1, Number(body.players) || 4));
  const job = await createJob({
    calibration: { frame_time_s: cal.frame_time_s, frame_size: cal.frame_size, image_points: points },
    durationS,
    sessionType: body.sessionType === "entrenamiento" ? "entrenamiento" : "partido",
    players,
    email: typeof body.email === "string" && body.email.includes("@") ? body.email.slice(0, 200) : undefined,
    videoExt: ext,
  });
  return NextResponse.json({ job }, { status: 201 });
}

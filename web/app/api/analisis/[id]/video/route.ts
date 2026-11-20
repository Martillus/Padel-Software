import { NextResponse } from "next/server";
import type { ReadableStream as WebReadableStream } from "node:stream/web";

import { isValidId, saveVideoAndStart } from "@/lib/jobs";

export const runtime = "nodejs";

/** Recibe el vídeo (PUT con el archivo como cuerpo) y arranca el análisis. */
export async function PUT(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (!isValidId(id) || id === "demo") return NextResponse.json({ error: "No encontrado." }, { status: 404 });
  const type = req.headers.get("content-type") ?? "";
  if (!type.startsWith("video/") && type !== "application/octet-stream") {
    return NextResponse.json({ error: "El archivo no es un vídeo." }, { status: 415 });
  }
  if (!req.body) return NextResponse.json({ error: "Falta el vídeo." }, { status: 400 });
  try {
    const job = await saveVideoAndStart(id, req.body as unknown as WebReadableStream<Uint8Array>);
    return NextResponse.json({ job });
  } catch (err) {
    return NextResponse.json({ error: (err as Error).message }, { status: 400 });
  }
}

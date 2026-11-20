import { NextResponse } from "next/server";

import { getAnalysis, isValidId } from "@/lib/jobs";

export async function GET(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (!isValidId(id)) return NextResponse.json({ error: "No encontrado." }, { status: 404 });
  const res = await getAnalysis(id);
  if (!res) return NextResponse.json({ error: "No encontrado." }, { status: 404 });
  return NextResponse.json(res, { headers: { "Cache-Control": "no-store" } });
}

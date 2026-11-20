import fs from "node:fs/promises";

import { getPhotoPath, isValidId } from "@/lib/jobs";

export async function GET(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const p = isValidId(id) ? await getPhotoPath(id) : null;
  if (!p) return new Response("No encontrado", { status: 404 });
  return new Response(new Uint8Array(await fs.readFile(p)), {
    headers: { "Content-Type": "image/jpeg", "Cache-Control": "private, max-age=3600" },
  });
}

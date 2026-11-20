import { NextResponse, type NextRequest } from "next/server";

import { ACCESS_COOKIE, accessMode, accessToken } from "@/lib/access";

export async function middleware(req: NextRequest) {
  const mode = accessMode();
  if (mode === "open") return NextResponse.next();
  if (mode === "password") {
    const cookie = req.cookies.get(ACCESS_COOKIE)?.value;
    if (cookie && cookie === (await accessToken(process.env.SITE_PASSWORD!))) return NextResponse.next();
  }
  if (req.nextUrl.pathname.startsWith("/api/")) {
    return NextResponse.json({ error: "Web privada: hace falta la contraseña." }, { status: 401 });
  }
  const url = req.nextUrl.clone();
  url.pathname = "/acceso";
  url.search = `?next=${encodeURIComponent(req.nextUrl.pathname + req.nextUrl.search)}`;
  return NextResponse.redirect(url);
}

export const config = {
  // Todo menos la propia pantalla de acceso y los archivos internos de Next.js.
  matcher: ["/((?!acceso|api/acceso|_next/static|_next/image|favicon.ico|robots.txt).*)"],
};

import { NextResponse } from "next/server";

import { ACCESS_COOKIE, accessMode, accessToken, safeNext } from "@/lib/access";

export async function POST(req: Request) {
  const form = await req.formData();
  const next = safeNext(String(form.get("next") ?? "/"));
  const password = String(form.get("password") ?? "");
  const base = new URL(req.url);
  if (accessMode() !== "password" || password !== process.env.SITE_PASSWORD) {
    await new Promise((r) => setTimeout(r, 600)); // frena los intentos a ciegas
    const back = new URL("/acceso", base);
    back.searchParams.set("next", next);
    back.searchParams.set("error", "1");
    return NextResponse.redirect(back, 303);
  }
  const res = NextResponse.redirect(new URL(next, base), 303);
  res.cookies.set(ACCESS_COOKIE, await accessToken(password), {
    httpOnly: true,
    secure: base.protocol === "https:",
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 24 * 30,
  });
  return res;
}

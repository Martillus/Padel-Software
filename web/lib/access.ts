// Acceso privado a la web (pantalla de contraseña). Funciona en el "edge" (middleware) y en Node.
//
// Reglas:
//  - SITE_PUBLIC=true            -> web abierta a todo el mundo
//  - SITE_PASSWORD=<contraseña>  -> hay que escribir la contraseña (se recuerda 30 días)
//  - sin nada, publicada en Vercel -> CERRADA (nunca queda pública por error)
//  - sin nada, en tu ordenador   -> abierta (para desarrollar)

export const ACCESS_COOKIE = "padel_acceso";

export type AccessMode = "open" | "password" | "locked";

export function accessMode(): AccessMode {
  if (process.env.SITE_PUBLIC === "true") return "open";
  if (process.env.SITE_PASSWORD) return "password";
  return process.env.VERCEL ? "locked" : "open";
}

/** Valor de la cookie: huella de la contraseña (si cambias la contraseña, todos deben volver a entrar). */
export async function accessToken(password: string): Promise<string> {
  const data = new TextEncoder().encode(`padel-acceso:v1:${password}`);
  const digest = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, "0")).join("");
}

/** Evita redirecciones a otras webs: solo rutas internas. */
export function safeNext(next: string | null | undefined): string {
  return next && next.startsWith("/") && !next.startsWith("//") ? next : "/";
}

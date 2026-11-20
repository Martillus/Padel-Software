import type { Metadata } from "next";

import { Logo } from "@/components/Logo";
import { accessMode, safeNext } from "@/lib/access";

export const metadata: Metadata = { title: "Acceso", robots: { index: false, follow: false } };
export const dynamic = "force-dynamic";

export default async function AccessPage({ searchParams }: { searchParams: Promise<{ next?: string; error?: string }> }) {
  const { next, error } = await searchParams;
  const mode = accessMode();
  return (
    <div className="mx-auto flex max-w-md flex-col items-center px-4 py-20">
      <Logo className="text-2xl" />
      <div className="card mt-8 w-full p-6">
        <h1 className="text-xl font-bold">Web privada</h1>
        {mode === "locked" ? (
          <p className="mt-2 text-muted">
            Esta versión de prueba todavía no tiene contraseña configurada, así que está cerrada. El responsable debe añadir la
            variable <code className="text-ink">SITE_PASSWORD</code> en Vercel.
          </p>
        ) : (
          <form action="/api/acceso" method="post" className="mt-4 space-y-4">
            <p className="text-muted">Es una versión de prueba. Escribe la contraseña para entrar.</p>
            <input type="hidden" name="next" value={safeNext(next)} />
            <input className="input" type="password" name="password" placeholder="Contraseña" autoComplete="current-password" required autoFocus aria-label="Contraseña" />
            {error && <p className="text-sm text-red-300">Contraseña incorrecta.</p>}
            <button className="btn-primary w-full">Entrar</button>
          </form>
        )}
      </div>
    </div>
  );
}

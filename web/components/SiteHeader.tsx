import Link from "next/link";

import { Logo } from "./Logo";

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-30 border-b border-line/70 bg-bg/85 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
        <Link href="/" aria-label="Inicio">
          <Logo className="text-lg" />
        </Link>
        <nav className="flex items-center gap-1 text-sm sm:gap-2">
          <Link href="/#como-funciona" className="hidden rounded-full px-3 py-2 text-muted hover:text-ink sm:block">
            Cómo funciona
          </Link>
          <Link href="/analisis/demo" className="hidden rounded-full px-3 py-2 text-muted hover:text-ink sm:block">
            Ver ejemplo
          </Link>
          <Link href="/mis-partidos" className="rounded-full px-3 py-2 text-muted hover:text-ink">
            Mis partidos
          </Link>
          <Link href="/subir" className="btn-primary !px-4 !py-2 text-sm">
            Analizar
          </Link>
        </nav>
      </div>
    </header>
  );
}

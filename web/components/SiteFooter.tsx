import Link from "next/link";

import { Logo } from "./Logo";

export function SiteFooter() {
  return (
    <footer className="mt-20 border-t border-line">
      <div className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-10 text-sm text-muted sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-2">
          <Logo />
          <p>Análisis de partidos de pádel con inteligencia artificial. Sin reconocimiento facial.</p>
        </div>
        <div className="flex gap-5">
          <Link href="/privacidad" className="hover:text-ink">Privacidad</Link>
          <Link href="/condiciones" className="hover:text-ink">Condiciones</Link>
          <Link href="/mis-partidos" className="hover:text-ink">Mis partidos</Link>
        </div>
      </div>
    </footer>
  );
}

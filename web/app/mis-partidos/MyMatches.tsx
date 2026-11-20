"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { readHistory, removeFromHistory, type HistoryItem } from "@/lib/history";

export function MyMatches() {
  const [items, setItems] = useState<HistoryItem[] | null>(null);
  useEffect(() => setItems(readHistory()), []);

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <h1 className="text-3xl font-extrabold tracking-tight">Mis partidos</h1>
      <p className="mt-2 text-muted">Sin cuentas ni contraseñas: tus análisis se guardan en este dispositivo. Guarda el enlace si quieres abrirlos desde otro.</p>
      {items === null ? null : items.length === 0 ? (
        <div className="card mt-8 p-8 text-center">
          <p className="text-lg font-semibold">Todavía no has analizado ningún partido</p>
          <div className="mt-6 flex flex-wrap justify-center gap-3">
            <Link href="/subir" className="btn-primary">Analizar mi partido</Link>
            <Link href="/analisis/demo" className="btn-ghost">Ver un ejemplo</Link>
          </div>
        </div>
      ) : (
        <ul className="mt-8 space-y-3">
          {items.map((it) => (
            <li key={it.id} className="card flex items-center justify-between gap-3 p-4">
              <Link href={`/analisis/${it.id}`} className="flex-1">
                <p className="font-bold">{it.title}</p>
                <p className="text-sm text-muted">{new Date(it.createdAt).toLocaleString("es-ES", { dateStyle: "medium", timeStyle: "short" })}</p>
              </Link>
              <button
                className="rounded-full px-3 py-2 text-sm text-muted hover:bg-surface-2 hover:text-ink"
                onClick={() => {
                  removeFromHistory(it.id);
                  setItems(readHistory());
                }}
              >
                Quitar
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

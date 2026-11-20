import type { Metadata } from "next";

export const metadata: Metadata = { title: "Condiciones" };

export default function TermsPage() {
  return (
    <article className="mx-auto max-w-3xl space-y-4 px-4 py-10 leading-relaxed">
      <p className="rounded-xl bg-amber-400/10 px-4 py-3 text-sm text-amber-200">
        BORRADOR pendiente de revisión por un abogado antes del lanzamiento. No es un texto legal definitivo.
      </p>
      <h1 className="text-3xl font-extrabold">Condiciones del servicio</h1>
      <h2 className="text-xl font-bold">Qué ofrecemos</h2>
      <p>Un análisis automático de un vídeo de pádel con estadísticas estimadas. Las cifras son aproximadas y no sustituyen el criterio de un entrenador.</p>
      <h2 className="text-xl font-bold">Tu responsabilidad al subir un vídeo</h2>
      <p>Al subir un vídeo confirmas que todas las personas que aparecen han aceptado que se grabe y se analice. No subas vídeos de terceros sin su permiso.</p>
      <h2 className="text-xl font-bold">Pago</h2>
      <p>[Pendiente: precio, momento del cobro, reembolsos si el vídeo no se puede analizar.]</p>
    </article>
  );
}

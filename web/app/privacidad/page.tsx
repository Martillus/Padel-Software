import type { Metadata } from "next";

export const metadata: Metadata = { title: "Privacidad" };

export default function PrivacyPage() {
  return (
    <article className="mx-auto max-w-3xl space-y-4 px-4 py-10 leading-relaxed">
      <p className="rounded-xl bg-amber-400/10 px-4 py-3 text-sm text-amber-200">
        BORRADOR pendiente de revisión por un abogado antes del lanzamiento. No es un texto legal definitivo.
      </p>
      <h1 className="text-3xl font-extrabold">Política de privacidad</h1>
      <h2 className="text-xl font-bold">Qué datos tratamos</h2>
      <p>El vídeo que subes, los puntos de la pista que marcas, las estadísticas calculadas y, si nos lo das, tu email para avisarte.</p>
      <h2 className="text-xl font-bold">Para qué</h2>
      <p>Solo para generar tu análisis y mostrártelo. No usamos reconocimiento facial: cada jugador se identifica por su posición en la pista.</p>
      <h2 className="text-xl font-bold">Inteligencia artificial</h2>
      <p>Los textos del informe y las respuestas del chat los genera un modelo de inteligencia artificial a partir de las estadísticas. Al modelo de lenguaje le enviamos solo cifras y etiquetas (J1, J2…), nunca el vídeo ni nombres.</p>
      <h2 className="text-xl font-bold">Tus vídeos no entrenan modelos</h2>
      <p>No usamos tus vídeos para entrenar modelos de inteligencia artificial sin tu permiso expreso.</p>
      <h2 className="text-xl font-bold">Conservación y borrado</h2>
      <p>[Pendiente de definir: plazo de borrado automático del vídeo y de los resultados.] Puedes pedirnos que borremos tus datos en cualquier momento.</p>
      <h2 className="text-xl font-bold">Contacto</h2>
      <p>[Pendiente: responsable del tratamiento, dirección y email de contacto.]</p>
    </article>
  );
}

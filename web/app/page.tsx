import Link from "next/link";

import { CourtHeatmap } from "@/components/court/CourtHeatmap";
import { RecordingTips } from "@/components/upload/RecordingTips";
import { APP_NAME, formatPrice, PRICE_EUR } from "@/lib/config";
import demo from "@/data/demo/analisis.json";

const STEPS = [
  { n: "1", title: "Graba con tu móvil", text: "Ponlo quieto detrás de la pista y juega como siempre. Sin cámaras especiales ni apps." },
  { n: "2", title: "Súbelo y marca la pista", text: "Eliges el vídeo y tocas 4 puntos de la pista en una imagen. Menos de un minuto." },
  { n: "3", title: "Descubre cómo has jugado", text: "Tu informe con estadísticas, mapa de calor y consejos. Y un entrenador IA para preguntarle lo que quieras." },
];

const FEATURES = [
  { icon: "🔥", title: "Mapa de calor", text: "Dónde has pasado el partido, de un vistazo." },
  { icon: "🏃", title: "Distancia y velocidad", text: "Metros recorridos, velocidad punta y ritmo por minuto." },
  { icon: "🎾", title: "Red, transición y fondo", text: "Cuánto subes a la red y cuánto te quedas en tierra de nadie." },
  { icon: "🤝", title: "Tu pareja", text: "Si subís y bajáis juntos o jugáis desalineados." },
  { icon: "🏆", title: "Logros para compartir", text: "«Dominio de la red», «Muro del fondo»… e imagen lista para Instagram." },
  { icon: "💬", title: "Entrenador IA", text: "Pregunta qué mejorar y qué ejercicios te vienen bien." },
];

const FAQ = [
  { q: "¿Necesito algo especial para grabar?", a: "No. Solo tu móvil, a ser posible en un trípode o apoyado en alto detrás de la pista." },
  { q: "¿Funciona con partidos de amigos?", a: "Sí, está pensado para jugadores amateur: partidos, pachangas o entrenamientos." },
  { q: "¿Reconocéis las caras?", a: "No. No usamos reconocimiento facial. Cada jugador se identifica por su posición y tú eliges cuál eres." },
  { q: "¿Qué tan exactas son las cifras?", a: "Son estimaciones. Las posiciones y las zonas son fiables con una buena grabación; la distancia puede variar un 10-20 %." },
  { q: "¿Contáis golpes y puntos ganados?", a: "Todavía no: estamos entrenando la IA para seguir la bola. Llegará en próximas versiones." },
  { q: "¿Qué pasa con mi vídeo?", a: "Es privado y solo se usa para tu análisis. No lo usamos para entrenar modelos sin tu permiso." },
];

export default function Home() {
  const near = demo.jugadores.find((p) => p.id === "J3") ?? demo.jugadores[0];
  return (
    <>
      {/* Portada */}
      <section className="relative overflow-hidden">
        <div className="pointer-events-none absolute -top-40 left-1/2 h-[520px] w-[900px] -translate-x-1/2 rounded-full bg-brand/25 blur-3xl" />
        <div className="relative mx-auto grid max-w-6xl items-center gap-12 px-4 pt-14 pb-16 sm:pt-20 lg:grid-cols-[1.1fr_.9fr]">
          <div>
            <span className="inline-flex items-center gap-2 rounded-full border border-line bg-surface px-3 py-1 text-xs font-semibold text-muted">
              <span className="h-2 w-2 rounded-full bg-ball" /> Análisis de pádel con inteligencia artificial
            </span>
            <h1 className="mt-5 text-4xl leading-[1.05] font-extrabold tracking-tight sm:text-6xl">
              Graba tu partido.
              <br />
              <span className="text-ball">Descubre cómo juegas.</span>
            </h1>
            <p className="mt-5 max-w-xl text-lg text-muted">
              Sube el vídeo de tu partido grabado con el móvil y recibe tus estadísticas: mapa de calor, metros recorridos, tiempo en la red y consejos para mejorar.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link href="/subir" className="btn-primary text-lg">Analizar mi partido</Link>
              <Link href="/analisis/demo" className="btn-ghost text-lg">Ver un ejemplo</Link>
            </div>
            <ul className="mt-8 flex flex-wrap gap-x-6 gap-y-2 text-sm text-muted">
              <li>✓ Solo con tu móvil</li>
              <li>✓ Sin crear cuenta</li>
              <li>✓ Sin reconocimiento facial</li>
            </ul>
          </div>

          {/* Vista previa del informe */}
          <div className="relative mx-auto w-full max-w-[340px]">
            <div className="rounded-[2.5rem] border border-line bg-surface p-3 shadow-2xl shadow-brand/20">
              <div className="rounded-[2rem] bg-bg p-4">
                <p className="text-xs font-semibold text-ball">Tu informe · J3</p>
                <p className="text-lg font-extrabold">🎾 Dominio de la red</p>
                <div className="mt-3 grid grid-cols-[110px_1fr] gap-3">
                  <CourtHeatmap cells={near.mapa_calor_celdas} label="Mapa de calor de ejemplo" className="[&_figcaption]:hidden" />
                  <div className="space-y-2">
                    {[
                      [`${Math.round(near.distancia_m)} m`, "recorridos"],
                      [`${Math.round(near.zonas_pct.red)}%`, "en la red"],
                      [`${(near.velocidad_punta_mps * 3.6).toFixed(1).replace(".", ",")} km/h`, "punta"],
                    ].map(([v, l]) => (
                      <div key={l} className="rounded-xl bg-surface-2 px-3 py-2">
                        <p className="text-lg leading-none font-extrabold">{v}</p>
                        <p className="text-[11px] text-muted">{l}</p>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="mt-3 rounded-2xl bg-surface-2 p-3 text-xs leading-relaxed">
                  <p className="font-bold text-ball">Entrenador IA</p>
                  Eres quien más tiempo pasa en la red de los cuatro. Para dar el siguiente paso, trabaja la salida hacia atrás cuando te tiran un globo.
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Cómo funciona */}
      <section id="como-funciona" className="mx-auto max-w-6xl scroll-mt-20 px-4 py-16">
        <h2 className="text-3xl font-extrabold tracking-tight sm:text-4xl">Así de fácil</h2>
        <div className="mt-8 grid gap-4 md:grid-cols-3">
          {STEPS.map((s) => (
            <div key={s.n} className="card p-6">
              <span className="flex h-10 w-10 items-center justify-center rounded-full bg-ball text-lg font-extrabold text-black">{s.n}</span>
              <h3 className="mt-4 text-xl font-bold">{s.title}</h3>
              <p className="mt-2 text-muted">{s.text}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Qué verás */}
      <section className="mx-auto max-w-6xl px-4 py-16">
        <h2 className="text-3xl font-extrabold tracking-tight sm:text-4xl">Lo que vas a descubrir</h2>
        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f) => (
            <div key={f.title} className="card p-6">
              <span className="text-3xl" aria-hidden="true">{f.icon}</span>
              <h3 className="mt-3 text-lg font-bold">{f.title}</h3>
              <p className="mt-1 text-muted">{f.text}</p>
            </div>
          ))}
        </div>
        <p className="mt-6 text-sm text-muted">Próximamente: golpes, puntos ganados y errores por jugador.</p>
      </section>

      {/* Ejemplo */}
      <section className="mx-auto max-w-6xl px-4 py-8">
        <div className="card flex flex-col items-start justify-between gap-6 bg-gradient-to-br from-brand/30 to-surface p-8 sm:flex-row sm:items-center">
          <div>
            <h2 className="text-2xl font-extrabold">¿Quieres verlo antes?</h2>
            <p className="mt-1 text-muted">Abre un análisis de ejemplo y prueba el chat con el entrenador IA.</p>
          </div>
          <Link href="/analisis/demo" className="btn-primary">Ver el ejemplo</Link>
        </div>
      </section>

      {/* Cómo grabar */}
      <section className="mx-auto max-w-6xl px-4 py-16">
        <h2 className="text-3xl font-extrabold tracking-tight sm:text-4xl">Cómo grabar tu partido</h2>
        <p className="mt-2 text-muted">La clave de un buen análisis es una buena grabación.</p>
        <RecordingTips className="mt-8" />
      </section>

      {/* Precio */}
      <section id="precio" className="mx-auto max-w-6xl scroll-mt-20 px-4 py-16">
        <div className="card mx-auto max-w-md p-8 text-center">
          <p className="font-semibold text-ball">Por partido</p>
          <p className="mt-2 text-5xl font-extrabold">{formatPrice(PRICE_EUR)}</p>
          <p className="mt-2 text-muted">Pagas solo cuando analizas. Sin suscripción.</p>
          <ul className="mt-6 space-y-2 text-left">
            {["Informe de los 4 jugadores", "Mapas de calor y estadísticas", "Logros e imagen para compartir", "Chat con el entrenador IA"].map((i) => (
              <li key={i} className="flex gap-2"><span className="text-ball">✓</span>{i}</li>
            ))}
          </ul>
          <Link href="/subir" className="btn-primary mt-8 w-full">Analizar mi partido</Link>
        </div>
      </section>

      {/* Preguntas frecuentes */}
      <section className="mx-auto max-w-3xl px-4 py-16">
        <h2 className="text-3xl font-extrabold tracking-tight">Preguntas frecuentes</h2>
        <div className="mt-6 space-y-3">
          {FAQ.map((f) => (
            <details key={f.q} className="card group p-5">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-semibold">
                {f.q}
                <span className="text-muted transition group-open:rotate-45">+</span>
              </summary>
              <p className="mt-3 text-muted">{f.a}</p>
            </details>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 pb-8 text-center">
        <h2 className="text-3xl font-extrabold tracking-tight sm:text-4xl">¿Jugamos?</h2>
        <p className="mt-2 text-muted">Tu próximo partido puede ser el primero que analices con {APP_NAME}.</p>
        <Link href="/subir" className="btn-primary mt-6 text-lg">Analizar mi partido</Link>
      </section>
    </>
  );
}

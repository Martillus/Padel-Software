import Anthropic from "@anthropic-ai/sdk";

import { CHAT_MAX_USER_MESSAGES } from "@/lib/config";
import { getAnalysis, isValidId } from "@/lib/jobs";
import type { Analysis } from "@/lib/types";

export const runtime = "nodejs";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

const SYSTEM = `Eres el entrenador virtual de una web de análisis de partidos de pádel amateur en España.
Hablas con un jugador que acaba de ver las estadísticas de su partido. Respondes en español de España,
de forma cercana, clara y breve (2-6 frases salvo que pida más detalle), con tono positivo y motivador.

Reglas:
- Usa SOLO los datos del partido que tienes abajo. Si algo no está en los datos, dilo con naturalidad.
- Los jugadores se llaman J1, J2, J3 y J4 (J1 y J2 juegan en el campo cercano a la cámara; J3 y J4 en el lejano).
  No inventes nombres. Si el usuario te dice quién es, háblale de tú sobre ese jugador.
- Todavía NO medimos golpes, tipos de golpe, puntos ganados ni errores: si te lo preguntan, explica que
  llegará pronto y ofrece lo que sí se puede decir con las posiciones.
- "Red" = a menos de 3,5 m de la red; "transición" = entre 3,5 m y la línea de saque (tierra de nadie); "fondo" = detrás de la línea de saque.
- Si recomiendas ejercicios, explica en una frase el porqué con los datos.
- Si el fragmento analizado es corto (menos de 2 minutos), recuerda que las conclusiones son orientativas.
- Nada de diagnósticos médicos ni promesas de resultados.`;

/** Lo mínimo necesario del análisis para el chat (sin mapas de calor celda a celda). */
function context(analysis: Analysis, reportMd?: string): string {
  const players = analysis.jugadores.map(({ mapa_calor_celdas: _m, ...p }) => p);
  return JSON.stringify(
    {
      duracion_analizada_s: analysis.video.duracion_analizada_s,
      jugadores: players,
      parejas: analysis.parejas,
      limitaciones: analysis.limitaciones,
      informe: reportMd ?? null,
    },
    null,
    1,
  );
}

function textStream(gen: () => AsyncGenerator<string>): Response {
  const enc = new TextEncoder();
  const stream = new ReadableStream<Uint8Array>({
    async start(controller) {
      try {
        for await (const chunk of gen()) controller.enqueue(enc.encode(chunk));
      } catch (err) {
        controller.enqueue(enc.encode(`\n\n[${errorMessage(err)}]`));
      } finally {
        controller.close();
      }
    },
  });
  return new Response(stream, { headers: { "Content-Type": "text/plain; charset=utf-8", "Cache-Control": "no-store" } });
}

function errorMessage(err: unknown): string {
  if (err instanceof Anthropic.AuthenticationError) return "La clave de la API de Claude no es válida.";
  if (err instanceof Anthropic.RateLimitError) return "Hay mucha demanda ahora mismo. Inténtalo en unos segundos.";
  if (err instanceof Anthropic.APIError) return `Error del servicio de IA (${err.status ?? "sin código"}). Inténtalo de nuevo.`;
  return "No se ha podido responder. Inténtalo de nuevo.";
}

export async function POST(req: Request) {
  let body: { id?: string; messages?: ChatMessage[]; focus?: string | null };
  try {
    body = await req.json();
  } catch {
    return new Response("Petición no válida.", { status: 400 });
  }
  const id = body.id ?? "";
  const messages = (body.messages ?? []).filter(
    (m) => (m.role === "user" || m.role === "assistant") && typeof m.content === "string" && m.content.trim(),
  );
  if (!isValidId(id) || !messages.length || messages[messages.length - 1].role !== "user") {
    return new Response("Petición no válida.", { status: 400 });
  }
  if (messages.filter((m) => m.role === "user").length > CHAT_MAX_USER_MESSAGES) {
    return new Response(`Has llegado al máximo de ${CHAT_MAX_USER_MESSAGES} preguntas para este partido.`, { status: 429 });
  }
  const data = await getAnalysis(id);
  if (!data?.analysis) return new Response("Análisis no disponible.", { status: 404 });

  // Sin clave: modo demostración, para poder probar la interfaz.
  if (!process.env.ANTHROPIC_API_KEY && !process.env.ANTHROPIC_AUTH_TOKEN) {
    return textStream(async function* () {
      const demo =
        "Ahora mismo el chat está en **modo demostración** porque falta configurar la clave de la API de Claude " +
        "(variable ANTHROPIC_API_KEY). Cuando esté puesta, aquí te responderé usando las estadísticas de tu partido: " +
        "dónde has jugado, cómo se ha coordinado tu pareja y qué ejercicios te vendrían bien.";
      for (const word of demo.split(" ")) {
        yield word + " ";
        await new Promise((r) => setTimeout(r, 25));
      }
    });
  }

  const focus = typeof body.focus === "string" && /^J\d$/.test(body.focus) ? body.focus : null;
  // Solo los últimos mensajes: la conversación no crece sin límite (coste y contexto).
  const history = messages.slice(-16).map((m) => ({ role: m.role, content: m.content.slice(0, 2000) }));
  const client = new Anthropic();

  return textStream(async function* () {
    const stream = client.beta.messages.stream({
      model: process.env.ANTHROPIC_MODEL ?? "claude-opus-5-5",
      max_tokens: 8000,
      output_config: { effort: (process.env.CHAT_EFFORT as "low" | "medium" | "high" | undefined) ?? "low" },
      // Si el modelo principal rechaza una petición, la API la reintenta con otro modelo.
      betas: ["server-side-fallback-2026-07-01"],
      fallbacks: "default",
      system: [
        { type: "text", text: SYSTEM },
        {
          type: "text",
          text: `Datos del partido (JSON):\n${context(data.analysis!, data.reportMd)}`,
          // Los datos del partido se repiten en cada pregunta: se guardan en caché y salen más baratos.
          cache_control: { type: "ephemeral" },
        },
        ...(focus ? [{ type: "text" as const, text: `El usuario ha dicho que es ${focus}.` }] : []),
      ],
      messages: history,
    });
    for await (const event of stream) {
      if (event.type === "content_block_delta" && event.delta.type === "text_delta") yield event.delta.text;
    }
    const final = await stream.finalMessage();
    if (final.stop_reason === "refusal") yield "\n\nNo puedo responder a eso. Prueba a preguntarme por tu partido.";
  });
}

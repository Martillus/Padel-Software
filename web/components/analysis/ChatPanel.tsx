"use client";

import { useEffect, useRef, useState } from "react";

import { CHAT_MAX_USER_MESSAGES } from "@/lib/config";

import { Markdown } from "../Markdown";

interface Msg {
  role: "user" | "assistant";
  content: string;
}

const SUGGESTIONS = [
  "¿Qué es lo que mejor he hecho?",
  "¿Qué ejercicio me recomiendas?",
  "¿Cómo se ha coordinado mi pareja?",
  "¿Por qué paso tanto tiempo en transición?",
];

/** Chat con la IA sobre el partido. Envía solo las preguntas; los datos los añade el servidor. */
export function ChatPanel({ analysisId, focus, onClose }: { analysisId: string; focus: string | null; onClose?: () => void }) {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const scroller = useRef<HTMLDivElement>(null);
  const userCount = messages.filter((m) => m.role === "user").length;
  const limitReached = userCount >= CHAT_MAX_USER_MESSAGES;

  useEffect(() => {
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  async function send(text: string) {
    const q = text.trim();
    if (!q || busy || limitReached) return;
    const next: Msg[] = [...messages, { role: "user", content: q }];
    setMessages([...next, { role: "assistant", content: "" }]);
    setInput("");
    setBusy(true);
    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: analysisId, messages: next, focus }),
      });
      if (!res.ok || !res.body) throw new Error((await res.text()) || "No se ha podido responder.");
      const reader = res.body.getReader();
      const dec = new TextDecoder();
      let acc = "";
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        acc += dec.decode(value, { stream: true });
        setMessages([...next, { role: "assistant", content: acc }]);
      }
    } catch (err) {
      setMessages([...next, { role: "assistant", content: (err as Error).message }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between gap-3 border-b border-line px-4 py-3">
        <div>
          <p className="font-bold">Pregunta a tu entrenador IA</p>
          <p className="text-xs text-muted">{focus ? `Hablando de ${focus}` : "Elige tu jugador para respuestas más personales"}</p>
        </div>
        {onClose && (
          <button onClick={onClose} className="rounded-full p-2 text-muted hover:bg-surface-2 hover:text-ink" aria-label="Cerrar chat">
            ✕
          </button>
        )}
      </div>
      <div ref={scroller} className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
        {!messages.length && (
          <div className="space-y-3">
            <p className="text-sm text-muted">Pregúntame lo que quieras sobre el partido. Algunas ideas:</p>
            <div className="flex flex-wrap gap-2">
              {SUGGESTIONS.map((s) => (
                <button key={s} onClick={() => send(s)} className="rounded-full border border-line px-3 py-1.5 text-left text-sm hover:border-ball hover:text-ball">
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={m.role === "user" ? "flex justify-end" : "flex justify-start"}>
            <div className={`max-w-[88%] rounded-2xl px-3.5 py-2.5 text-[15px] leading-relaxed ${m.role === "user" ? "bg-brand text-white" : "bg-surface-2"}`}>
              {m.role === "assistant" ? (
                m.content ? <Markdown text={m.content} className="prose-chat" /> : <span className="inline-flex gap-1 py-1" aria-label="Escribiendo">
                  <span className="h-2 w-2 animate-bounce rounded-full bg-muted" />
                  <span className="h-2 w-2 animate-bounce rounded-full bg-muted [animation-delay:.15s]" />
                  <span className="h-2 w-2 animate-bounce rounded-full bg-muted [animation-delay:.3s]" />
                </span>
              ) : (
                m.content
              )}
            </div>
          </div>
        ))}
      </div>
      <form
        className="flex gap-2 border-t border-line p-3"
        onSubmit={(e) => {
          e.preventDefault();
          void send(input);
        }}
      >
        <input
          className="input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={limitReached ? "Has llegado al máximo de preguntas" : "Escribe tu pregunta…"}
          maxLength={500}
          disabled={busy || limitReached}
          aria-label="Tu pregunta"
        />
        <button className="btn-primary !px-4" disabled={busy || !input.trim() || limitReached} aria-label="Enviar">
          ➤
        </button>
      </form>
      <p className="px-4 pb-3 text-[11px] text-muted">
        Respuestas generadas con IA a partir de las estadísticas. Pueden contener errores. {userCount}/{CHAT_MAX_USER_MESSAGES} preguntas.
      </p>
    </div>
  );
}

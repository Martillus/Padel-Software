"""Informe en español para el entrenador.

Dos caminos:
1. Con ``ANTHROPIC_API_KEY`` configurada: un modelo de lenguaje (Claude) redacta el
   informe a partir de las métricas y de las observaciones/ejercicios de las reglas.
2. Sin clave o si falla la llamada: un informe de plantilla, sin IA, con las mismas
   observaciones. Así el motor nunca se queda sin informe.

Privacidad (importante con menores): al modelo de lenguaje SOLO se le envían métricas
numéricas y etiquetas J1..J4. Ni vídeo, ni imágenes, ni nombres, ni edades. Los nombres
reales se sustituyen después, en nuestro servidor.
"""

from __future__ import annotations

import json
import logging
import os
import re

from .recommendations import EXERCISES

log = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-opus-5-5"

AI_NOTICE = (
    "_Este informe se ha generado automáticamente con inteligencia artificial a partir del "
    "vídeo. Las cifras son estimaciones y deben ser revisadas por el entrenador._"
)

SYSTEM_PROMPT = """Eres un asistente para entrenadores de pádel en España. Recibes métricas \
calculadas automáticamente a partir de un vídeo grabado con móvil desde detrás de la pista, \
y redactas un informe en español de España, claro y accionable, que el entrenador pueda \
compartir con el alumno o con sus padres.

Reglas:
- Los jugadores se llaman J1, J2, J3... Usa exactamente esas etiquetas; no inventes nombres.
- Usa solo los datos proporcionados. No inventes golpes, errores, resultados ni tipos de golpe.
- Los datos marcados como "experimental" (golpes estimados) son poco fiables: menciónalos con cautela o no los menciones.
- Si la cobertura de un jugador es baja, dilo y sé prudente con sus conclusiones.
- Recomienda ejercicios preferentemente de la lista proporcionada, explicando el porqué con los datos.
- Tono positivo y constructivo (puede haber menores de edad): empieza por lo que hace bien.
- Usa unidades comprensibles (metros, %, minutos). Nada de jerga técnica de visión por computador.
- Formato Markdown: un apartado "## Resumen de la sesión", un apartado "## J1" etc. por jugador \
(Puntos fuertes, A mejorar, Ejercicios recomendados) y, si hay datos de pareja, "## Trabajo en pareja".
- Máximo unas 500 palabras en total."""


def build_llm_payload(analysis: dict, context: dict | None = None) -> dict:
    """Extrae lo mínimo necesario para el informe (minimización de datos, RGPD art. 5.1.c)."""
    players = []
    for p in analysis["jugadores"]:
        players.append({k: v for k, v in p.items() if not k.startswith("_") and k != "observaciones"} | {"observaciones": p.get("observaciones", [])})
    return {
        "contexto": {
            "tipo_sesion": (context or {}).get("tipo_sesion", "desconocido"),
            "nivel": (context or {}).get("nivel", "desconocido"),
            "duracion_analizada_s": analysis["video"]["duracion_analizada_s"],
        },
        "jugadores": players,
        "parejas": analysis.get("parejas", []),
        "ejercicios_disponibles": EXERCISES,
        "limitaciones": analysis.get("limitaciones", []),
    }


def generate_with_llm(payload: dict, model: str | None = None) -> tuple[str, dict]:
    import anthropic

    client = anthropic.Anthropic()  # lee ANTHROPIC_API_KEY del entorno
    model = model or os.getenv("PADEL_LLM_MODEL", DEFAULT_MODEL)
    response = client.beta.messages.create(
        model=model,
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        output_config={"effort": os.getenv("PADEL_LLM_EFFORT", "medium")},
        # Si el modelo principal rechaza la petición, la API reintenta con otro modelo.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        messages=[
            {
                "role": "user",
                "content": "Métricas de la sesión en JSON:\n\n" + json.dumps(payload, ensure_ascii=False, indent=1),
            }
        ],
    )
    if response.stop_reason == "refusal":
        raise RuntimeError("El modelo rechazó generar el informe.")
    text = "".join(b.text for b in response.content if b.type == "text").strip()
    if not text:
        raise RuntimeError("Respuesta vacía del modelo.")
    usage = {
        "modelo": response.model,
        "tokens_entrada": response.usage.input_tokens,
        "tokens_salida": response.usage.output_tokens,
    }
    return text, usage


def _n(x) -> str:
    """Número con coma decimal (formato español)."""
    return str(x).replace(".", ",")


def generate_template(analysis: dict) -> str:
    lines = ["## Resumen de la sesión", ""]
    dur = analysis["video"]["duracion_analizada_s"]
    lines.append(f"Se han analizado {_n(round(dur / 60, 1))} minutos de vídeo y se han identificado {len(analysis['jugadores'])} jugadores.")
    lines.append("")
    for p in analysis["jugadores"]:
        z = p["zonas_pct"]
        lines += [
            f"## {p['id']}",
            "",
            f"- Campo: {p['campo']} · lado habitual: {p['lado_habitual']} · visible el {_n(p['cobertura_pct'])}% del tiempo",
            f"- Distancia recorrida: {_n(p['distancia_m'])} m ({_n(p['metros_por_minuto'])} m/min) · velocidad punta: {_n(p['velocidad_punta_mps'])} m/s",
            f"- Tiempo por zona: red {_n(z['red'])}% · transición {_n(z['transicion'])}% · fondo {_n(z['fondo'])}%",
            "",
        ]
        fortalezas = [o for o in p.get("observaciones", []) if o["tipo"] == "fortaleza"]
        mejoras = [o for o in p.get("observaciones", []) if o["tipo"] in ("mejora", "aviso")]
        if fortalezas:
            lines += ["**Puntos fuertes**", ""] + [f"- {o['texto']}" for o in fortalezas] + [""]
        if mejoras:
            lines += ["**A mejorar**", ""] + [f"- {o['texto']}" for o in mejoras] + [""]
        ejercicios = {o["ejercicio"] for o in p.get("observaciones", []) if o.get("ejercicio")}
        if ejercicios:
            lines += ["**Ejercicios recomendados**", ""]
            lines += [f"- **{EXERCISES[e]['nombre']}**: {EXERCISES[e]['descripcion']}" for e in sorted(ejercicios)] + [""]
    if analysis.get("parejas"):
        lines += ["## Trabajo en pareja", ""]
        for pair in analysis["parejas"]:
            lines.append(
                f"- {' y '.join(pair['jugadores'])} ({pair['campo']}): ambos en red {_n(pair['ambos_en_red_pct'])}% · "
                f"ambos en fondo {_n(pair['ambos_en_fondo_pct'])}% · desalineados {_n(pair['desalineados_pct'])}%"
            )
            lines += [f"  - {o['texto']}" for o in pair.get("observaciones", [])]
        lines.append("")
    return "\n".join(lines)


def apply_player_names(text: str, names: dict[str, str] | None) -> str:
    """Sustituye J1, J2... por los nombres que el entrenador ha asignado (en local)."""
    if not names:
        return text
    for pid, name in sorted(names.items(), key=lambda kv: -len(kv[0])):
        text = re.sub(rf"\b{re.escape(pid)}\b", name, text)
    return text


def build_report(analysis: dict, use_llm: bool = True, context: dict | None = None, names: dict[str, str] | None = None) -> tuple[str, dict]:
    meta: dict = {"generado_con_ia": False}
    body = None
    if use_llm and os.getenv("ANTHROPIC_API_KEY"):
        try:
            body, usage = generate_with_llm(build_llm_payload(analysis, context))
            meta = {"generado_con_ia": True, **usage}
        except Exception as exc:  # el informe de plantilla siempre está disponible
            log.warning("Fallo al generar el informe con IA (%s); uso la plantilla.", exc)
            meta["error_ia"] = str(exc)
    if body is None:
        body = generate_template(analysis)
    header = "# Informe de la sesión\n\n" + (AI_NOTICE + "\n\n" if meta["generado_con_ia"] else "_Informe automático generado a partir del vídeo; las cifras son estimaciones._\n\n")
    return apply_player_names(header + body, names), meta

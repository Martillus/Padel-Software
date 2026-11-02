"""Reglas sencillas que convierten métricas en observaciones y ejercicios sugeridos.

Son deterministas y explicables (el entrenador puede ver por qué salen). El modelo de
lenguaje las usa como base para redactar el informe, así evitamos que "invente"
ejercicios sin relación con los datos. Los umbrales son orientativos: hay que ajustarlos
con entrenadores reales durante el piloto y, a ser posible, por nivel del alumno.
"""

from __future__ import annotations


def _n(x) -> str:
    return str(x).replace(".", ",")


EXERCISES = {
    "subir_red": {
        "nombre": "Globo + subida a la red",
        "descripcion": "El entrenador lanza globo cortado; el alumno golpea de fondo y sube a la red tras el golpe en 3 apoyos, terminando con una volea.",
    },
    "salir_transicion": {
        "nombre": "Volea de transición y cierre",
        "descripcion": "Desde la línea de saque, volea baja bloqueada y dos pasos rápidos hacia la red. Series de 8 bolas, insistiendo en no quedarse parado en tierra de nadie.",
    },
    "pareja_alineada": {
        "nombre": "Desplazamientos en pareja con cuerda",
        "descripcion": "La pareja se mueve unida (sin bola o con cuerda de 3 m): sube y baja a la vez siguiendo la bola del entrenador.",
    },
    "defensa_fondo": {
        "nombre": "Defensa de pared de fondo",
        "descripcion": "Bolas a la pared de fondo; el alumno sale de la pared con salida de cristal y devuelve con globo profundo.",
    },
    "intensidad": {
        "nombre": "Desplazamientos laterales con cambio de ritmo",
        "descripcion": "Series de 30 s de desplazamiento lateral con toques a conos y volea al final. 4-6 series con descanso igual.",
    },
}


def player_insights(p: dict) -> list[dict]:
    z = p["zonas_pct"]
    out: list[dict] = []
    if z["transicion"] >= 30:
        out.append({"tipo": "mejora", "texto": f"Pasa el {_n(z['transicion'])}% del tiempo en zona de transición (tierra de nadie).", "ejercicio": "salir_transicion"})
    if z["red"] < 25 and z["fondo"] > 55:
        out.append({"tipo": "mejora", "texto": f"Solo está en la red el {_n(z['red'])}% del tiempo; juega muy atrás.", "ejercicio": "subir_red"})
    if z["red"] >= 45:
        out.append({"tipo": "fortaleza", "texto": f"Buena presencia en la red ({_n(z['red'])}% del tiempo).", "ejercicio": None})
    if z["fondo"] >= 70:
        out.append({"tipo": "mejora", "texto": "Juega casi siempre en el fondo: conviene trabajar salidas de pared y defensa.", "ejercicio": "defensa_fondo"})
    if p["metros_por_minuto"] and p["metros_por_minuto"] < 25 and p["tiempo_visible_s"] > 60:
        out.append({"tipo": "mejora", "texto": f"Se desplaza poco ({_n(p['metros_por_minuto'])} m/min).", "ejercicio": "intensidad"})
    if p["cobertura_pct"] < 50:
        out.append({"tipo": "aviso", "texto": f"Solo se le ha visto el {_n(p['cobertura_pct'])}% del vídeo; las cifras son menos fiables.", "ejercicio": None})
    return out


def pair_insights(pair: dict) -> list[dict]:
    out: list[dict] = []
    if pair["desalineados_pct"] >= 20:
        out.append(
            {
                "tipo": "mejora",
                "texto": f"La pareja {' y '.join(pair['jugadores'])} está desalineada (uno en red y otro en fondo) el {_n(pair['desalineados_pct'])}% del tiempo.",
                "ejercicio": "pareja_alineada",
            }
        )
    if pair["ambos_en_red_pct"] >= 40:
        out.append({"tipo": "fortaleza", "texto": f"La pareja {' y '.join(pair['jugadores'])} sube junta a la red con frecuencia ({_n(pair['ambos_en_red_pct'])}%).", "ejercicio": None})
    return out

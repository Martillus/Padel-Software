"""Página del informe para el jugador (``informe.html``, un único archivo).

Es lo que recibe el cliente por enlace tras pagar: funciona en el móvil, sin cuenta y sin
instalar nada. Todo va dentro del archivo (imágenes incluidas), así se puede guardar tal
cual en el almacenamiento y servir con un enlace privado.

* "¿Quién eres?": el jugador toca su figura en una foto del partido (sin reconocimiento facial).
* Estadísticas de los 4, logros ("Dominio de la red", "Más metros recorridos"...), parejas.
* Imagen para compartir en redes: se dibuja en el propio móvil. El nombre que escribe el
  jugador no sale de su teléfono.
"""

from __future__ import annotations

import base64
import html
import json
import re
from pathlib import Path

PLAYER_COLORS = {"J1": "#ffcc00", "J2": "#ff4d4d", "J3": "#4dff88", "J4": "#d580ff", "J5": "#ffffff", "J6": "#00e5ff"}


def _b64(path: Path, mime: str) -> str | None:
    if not path.exists():
        return None
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def _inline_md(text: str) -> str:
    t = html.escape(text)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<!\w)_(.+?)_(?!\w)", r"<em>\1</em>", t)
    return t


def markdown_sections(md: str) -> dict[str, str]:
    """Convierte el informe Markdown en HTML sencillo, separado por apartados ("## J1"...)."""
    sections: dict[str, list[str]] = {}
    current = "_intro"
    for line in md.splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            sections.setdefault(current, [])
            continue
        if line.startswith("# "):
            continue
        sections.setdefault(current, []).append(line)

    out: dict[str, str] = {}
    for name, lines in sections.items():
        parts: list[str] = []
        in_list = False
        for raw in lines:
            line = raw.rstrip()
            item = re.match(r"^\s*[-*] (.*)", line)
            if item:
                if not in_list:
                    parts.append("<ul>")
                    in_list = True
                parts.append(f"<li>{_inline_md(item.group(1))}</li>")
                continue
            if in_list:
                parts.append("</ul>")
                in_list = False
            if not line.strip():
                continue
            if line.startswith("### "):
                parts.append(f"<h4>{_inline_md(line[4:])}</h4>")
            elif line.startswith("> "):
                parts.append(f'<p class="nota">{_inline_md(line[2:])}</p>')
            else:
                parts.append(f"<p>{_inline_md(line)}</p>")
        if in_list:
            parts.append("</ul>")
        out[name] = "\n".join(parts)
    return out


def observations_html(observations: list[dict]) -> str:
    """Observaciones de las reglas (sin IA): avisos, puntos fuertes, a mejorar y ejercicios."""
    from .recommendations import EXERCISES

    avisos = [o for o in observations if o["tipo"] == "aviso"]
    fuertes = [o for o in observations if o["tipo"] == "fortaleza"]
    mejoras = [o for o in observations if o["tipo"] == "mejora"]
    ejercicios = sorted({o["ejercicio"] for o in observations if o.get("ejercicio")})
    parts = [f'<p class="nota">{html.escape(o["texto"])}</p>' for o in avisos]
    if fuertes:
        parts.append("<h4>Lo que haces bien</h4><ul>" + "".join(f"<li>{html.escape(o['texto'])}</li>" for o in fuertes) + "</ul>")
    if mejoras:
        parts.append("<h4>Para mejorar</h4><ul>" + "".join(f"<li>{html.escape(o['texto'])}</li>" for o in mejoras) + "</ul>")
    if ejercicios:
        parts.append(
            "<h4>Ejercicios recomendados</h4><ul>"
            + "".join(f"<li><strong>{html.escape(EXERCISES[e]['nombre'])}</strong>: {html.escape(EXERCISES[e]['descripcion'])}</li>" for e in ejercicios)
            + "</ul>"
        )
    return "\n".join(parts)


def compute_badges(players: list[dict]) -> dict[str, list[dict]]:
    """Logros del partido, comparando a los jugadores entre sí (nombres neutros)."""
    badges: dict[str, list[dict]] = {p["id"]: [] for p in players}
    if not players:
        return badges

    def award(key, icon, title, desc, minimum=None):
        best = max(players, key=key)
        if minimum is None or key(best) >= minimum:
            badges[best["id"]].append({"icono": icon, "titulo": title, "descripcion": desc})

    award(lambda p: p["distancia_m"], "🏃", "Más metros recorridos", "Quien más ha corrido del partido")
    award(lambda p: p["zonas_pct"]["red"], "🎾", "Dominio de la red", "Más tiempo jugando en la red", 25)
    award(lambda p: p["zonas_pct"]["fondo"], "🧱", "Muro del fondo", "Más tiempo defendiendo desde el fondo", 40)
    award(lambda p: p["velocidad_punta_mps"], "⚡", "Máxima velocidad", "El desplazamiento más rápido del partido")
    for p in players:
        if not badges[p["id"]]:
            z = p["zonas_pct"]
            if max(z.values()) < 50:
                badges[p["id"]].append({"icono": "🔄", "titulo": "Todoterreno", "descripcion": "Juega repartido entre red, transición y fondo"})
            else:
                badges[p["id"]].append({"icono": "🎯", "titulo": "Constancia", "descripcion": "Presente en todo el partido"})
    return badges


def build_html_report(analysis: dict, out_dir: str | Path, title: str = "Informe del partido") -> Path:
    out_dir = Path(out_dir)
    md_path = out_dir / analysis.get("informe", {}).get("archivo", "informe.md")
    sections = markdown_sections(md_path.read_text(encoding="utf-8")) if md_path.exists() else {}

    con_ia = bool(analysis.get("informe", {}).get("generado_con_ia"))
    players = []
    for p in analysis["jugadores"]:
        players.append(
            {
                "id": p["id"],
                "color": PLAYER_COLORS.get(p["id"], "#ffffff"),
                "campo": p["campo"],
                "lado": p["lado_habitual"],
                "distancia_m": p["distancia_m"],
                "m_min": p["metros_por_minuto"],
                "vel_punta_kmh": round(p["velocidad_punta_mps"] * 3.6, 1),
                "zonas": p["zonas_pct"],
                "cobertura": p["cobertura_pct"],
                "cortado": p.get("tiempo_cortado_pct", 0.0),
                "sprints": p["sprints"]["num"],
                "golpes": p["golpes_estimados"]["num"],
                "mapa": _b64(out_dir / (p.get("mapa_calor_web_png") or p.get("mapa_calor_png", "")), "image/png")
                if (p.get("mapa_calor_web_png") or p.get("mapa_calor_png"))
                else None,
                "texto": sections.get(p["id"], "") if con_ia else observations_html(p.get("observaciones", [])),
            }
        )
    badges = compute_badges(analysis["jugadores"])
    pair_obs = [o for q in analysis.get("parejas", []) for o in q.get("observaciones", [])]
    snap = analysis.get("foto_jugadores")
    data = {
        "titulo": title,
        "duracion_s": analysis["video"]["duracion_analizada_s"],
        "jugadores": players,
        "logros": badges,
        "parejas": [
            {
                "campo": q["campo"],
                "jugadores": q["jugadores"],
                "red": q["ambos_en_red_pct"],
                "fondo": q["ambos_en_fondo_pct"],
                "desalineados": q["desalineados_pct"],
                "distancia": q["distancia_media_entre_ellos_m"],
            }
            for q in analysis.get("parejas", [])
        ],
        # Sin IA, el texto de plantilla repetiría las cifras de las tarjetas: solo se muestran observaciones.
        "resumen_html": (sections.get("Resumen de la sesión", "") or sections.get("_intro", "")) if con_ia else "",
        "parejas_html": sections.get("Trabajo en pareja", "") if con_ia else observations_html(pair_obs),
        "foto": {
            "src": _b64(out_dir / snap["archivo"], "image/jpeg"),
            "ancho": snap["ancho"],
            "alto": snap["alto"],
            "cajas": snap["cajas"],
        }
        if snap
        else None,
        "limitaciones": analysis.get("limitaciones", []),
        "con_ia": con_ia,
    }
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    page = TEMPLATE.replace("__TITLE__", html.escape(title)).replace("__DATA__", payload)
    path = out_dir / "informe.html"
    path.write_text(page, encoding="utf-8")
    return path


TEMPLATE = r"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>__TITLE__</title>
<style>
:root {
  --bg: #f4f6fb; --card: #ffffff; --ink: #0f1a2e; --muted: #5b6780; --line: #e3e8f2;
  --accent: #1d5fd1; --accent-ink: #ffffff; --court: #2f6db5; --warn-bg: #fff6e0; --warn-ink: #7a5200;
  --red: #1d9e5c; --trans: #e3a008; --fondo: #6b7a99;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #0b1220; --card: #141d30; --ink: #e8edf7; --muted: #9aa6bf; --line: #24304a;
    --accent: #5b8ff0; --accent-ink: #0b1220; --warn-bg: #3a2e10; --warn-ink: #ffd98a;
  }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink); font: 16px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
main { max-width: 760px; margin: 0 auto; padding: 16px 16px 48px; }
header.top { background: linear-gradient(135deg, #0b3d91, #1d5fd1); color: #fff; padding: 22px 16px 26px; }
header.top .wrap { max-width: 760px; margin: 0 auto; }
header.top .kicker { font-size: 13px; letter-spacing: .08em; text-transform: uppercase; opacity: .8; }
header.top h1 { margin: 4px 0 6px; font-size: 26px; line-height: 1.2; }
header.top .meta { opacity: .9; font-size: 14px; }
.card { background: var(--card); border: 1px solid var(--line); border-radius: 16px; padding: 16px; margin-top: 16px; }
.card h2 { margin: 0 0 10px; font-size: 19px; }
.card h3 { margin: 16px 0 8px; font-size: 16px; }
.muted { color: var(--muted); font-size: 14px; }
.foto { position: relative; width: 100%; border-radius: 12px; overflow: hidden; background: #000; }
.foto img { display: block; width: 100%; height: auto; }
.foto button.caja { position: absolute; border: 3px solid var(--c); background: transparent; border-radius: 6px; cursor: pointer; padding: 0; }
.foto button.caja span { position: absolute; top: -26px; left: 50%; transform: translateX(-50%); background: var(--c); color: #111; font-weight: 700; font-size: 13px; padding: 1px 8px; border-radius: 10px; white-space: nowrap; }
.foto button.caja.activa { box-shadow: 0 0 0 3px #fff, 0 0 18px var(--c); }
.chips { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; }
.chip { border: 2px solid var(--c); background: transparent; color: var(--ink); border-radius: 999px; padding: 6px 14px; font-weight: 600; cursor: pointer; font-size: 15px; }
.chip.activa { background: var(--c); color: #111; }
.tiles { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
@media (min-width: 560px) { .tiles { grid-template-columns: repeat(4, 1fr); } }
.tile { background: var(--bg); border-radius: 12px; padding: 12px; }
.tile .v { font-size: 22px; font-weight: 750; line-height: 1.1; font-variant-numeric: tabular-nums; }
.tile .l { font-size: 13px; color: var(--muted); margin-top: 4px; }
.bar { display: flex; height: 14px; border-radius: 7px; overflow: hidden; margin: 6px 0 4px; }
.bar div { height: 100%; }
.leyenda { display: flex; gap: 14px; flex-wrap: wrap; font-size: 13px; color: var(--muted); }
.leyenda i { display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 5px; vertical-align: -1px; }
.logros { display: flex; flex-wrap: wrap; gap: 8px; }
.logro { display: flex; gap: 8px; align-items: center; background: var(--bg); border-radius: 12px; padding: 8px 12px; }
.logro b { display: block; font-size: 14px; }
.logro small { color: var(--muted); font-size: 12px; }
.dos { display: grid; gap: 16px; }
@media (min-width: 560px) { .dos { grid-template-columns: 180px 1fr; align-items: start; } }
.mapa img { width: 100%; max-width: 220px; border-radius: 10px; display: block; margin: 0 auto; }
.texto p, .texto li { margin: 6px 0; }
.texto ul { padding-left: 20px; margin: 6px 0; }
.nota { background: var(--warn-bg); color: var(--warn-ink); border-radius: 10px; padding: 10px 12px; font-size: 14px; }
.btn { display: inline-flex; gap: 8px; align-items: center; justify-content: center; background: var(--accent); color: var(--accent-ink); border: 0; border-radius: 12px; padding: 12px 18px; font-weight: 700; font-size: 16px; cursor: pointer; width: 100%; margin-top: 12px; }
label.nombre { display: block; font-size: 14px; color: var(--muted); margin-top: 12px; }
input[type=text] { width: 100%; font-size: 16px; padding: 10px 12px; border-radius: 10px; border: 1px solid var(--line); background: var(--bg); color: var(--ink); margin-top: 4px; }
.pareja { display: flex; justify-content: space-between; gap: 12px; padding: 10px 0; border-top: 1px solid var(--line); }
.pareja:first-of-type { border-top: 0; }
.pareja .nums { text-align: right; font-size: 14px; color: var(--muted); }
.punto { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 4px; vertical-align: 0; }
footer { margin-top: 20px; color: var(--muted); font-size: 13px; }
footer details { margin-top: 8px; }
[hidden] { display: none !important; }
</style>
</head>
<body>
<header class="top"><div class="wrap">
  <div class="kicker">Análisis de pádel con IA</div>
  <h1 id="titulo"></h1>
  <div class="meta" id="meta"></div>
</div></header>
<main>
  <section class="card" id="elige">
    <h2>¿Quién eres?</h2>
    <p class="muted">Toca tu figura en la foto para ver tu informe.</p>
    <div class="foto" id="foto" hidden></div>
    <div class="chips" id="chips"></div>
  </section>

  <section class="card" id="jugador" hidden>
    <h2 id="j-titulo"></h2>
    <div class="muted" id="j-sub"></div>
    <div class="logros" id="j-logros" style="margin-top:12px"></div>
    <h3>Tus números</h3>
    <div class="tiles" id="j-tiles"></div>
    <h3>¿Dónde has jugado?</h3>
    <div class="bar" id="j-bar"></div>
    <div class="leyenda" id="j-leyenda"></div>
    <div class="dos" style="margin-top:14px">
      <div class="mapa" id="j-mapa"></div>
      <div class="texto" id="j-texto"></div>
    </div>
    <h3>Compártelo</h3>
    <label class="nombre" for="nombre">Tu nombre para la imagen (se queda en tu móvil)</label>
    <input type="text" id="nombre" maxlength="24" placeholder="Por ejemplo: Martín" autocomplete="off">
    <button class="btn" id="compartir" type="button">Descargar imagen para compartir</button>
  </section>

  <section class="card" id="partido">
    <h2>El partido</h2>
    <div class="tiles" id="p-tiles"></div>
    <div class="texto" id="p-resumen" style="margin-top:10px"></div>
    <h3>Logros del partido</h3>
    <div class="logros" id="p-logros"></div>
    <h3>Parejas</h3>
    <div id="p-parejas"></div>
  </section>

  <footer>
    <div id="aviso-ia"></div>
    <details><summary>Cómo se ha calculado y limitaciones</summary><ul id="limitaciones"></ul></details>
  </footer>
</main>
<canvas id="lienzo" width="1080" height="1350" hidden></canvas>
<script id="datos" type="application/json">__DATA__</script>
<script>
(function () {
  "use strict";
  var D = JSON.parse(document.getElementById("datos").textContent);
  var byId = {};
  D.jugadores.forEach(function (p) { byId[p.id] = p; });
  var $ = function (id) { return document.getElementById(id); };
  var fmt = function (n, d) { return Number(n).toLocaleString("es-ES", { maximumFractionDigits: d == null ? 1 : d }); };
  var esc = function (s) { var e = document.createElement("span"); e.textContent = s; return e.innerHTML; };
  var ZONAS = [["red", "Red", "var(--red)", "#1d9e5c"], ["transicion", "Transición", "var(--trans)", "#e3a008"], ["fondo", "Fondo", "var(--fondo)", "#6b7a99"]];
  var actual = null;

  $("titulo").textContent = D.titulo;
  var min = D.duracion_s / 60;
  $("meta").textContent = (min >= 1 ? fmt(min, 0) + " min" : fmt(D.duracion_s, 0) + " s") + " analizados · " + D.jugadores.length + " jugadores";

  function lugar(p) { return "Campo " + (p.campo === "cerca" ? "cercano a la cámara" : "lejano") + ", lado " + p.lado; }
  function tile(v, l) { return '<div class="tile"><div class="v">' + v + '</div><div class="l">' + l + "</div></div>"; }
  function logroHTML(b, pid) {
    var who = pid ? ' <span class="punto" style="background:' + byId[pid].color + '"></span>' + pid : "";
    return '<div class="logro"><span style="font-size:22px">' + b.icono + "</span><div><b>" + esc(b.titulo) + who + "</b><small>" + esc(b.descripcion) + "</small></div></div>";
  }

  // Foto con figuras tocables
  if (D.foto && D.foto.src) {
    var f = $("foto"); f.hidden = false;
    var img = document.createElement("img"); img.src = D.foto.src; img.alt = "Foto del partido con los jugadores marcados"; f.appendChild(img);
    Object.keys(D.foto.cajas).forEach(function (pid) {
      var c = D.foto.cajas[pid], p = byId[pid]; if (!p) return;
      var b = document.createElement("button");
      b.className = "caja"; b.type = "button"; b.dataset.pid = pid; b.setAttribute("aria-label", "Soy " + pid);
      b.style.setProperty("--c", p.color);
      var pad = 0.25 * (c[2] - c[0]);
      b.style.left = (100 * (c[0] - pad) / D.foto.ancho) + "%";
      b.style.top = (100 * c[1] / D.foto.alto) + "%";
      b.style.width = (100 * (c[2] - c[0] + 2 * pad) / D.foto.ancho) + "%";
      b.style.height = (100 * (c[3] - c[1]) / D.foto.alto) + "%";
      b.innerHTML = "<span>" + pid + "</span>";
      b.addEventListener("click", function () { elegir(pid, true); });
      f.appendChild(b);
    });
  }
  D.jugadores.forEach(function (p) {
    var b = document.createElement("button");
    b.className = "chip"; b.type = "button"; b.dataset.pid = p.id; b.textContent = p.id;
    b.style.setProperty("--c", p.color);
    b.addEventListener("click", function () { elegir(p.id, true); });
    $("chips").appendChild(b);
  });

  function elegir(pid, scroll) {
    var p = byId[pid]; if (!p) return;
    actual = pid;
    try { history.replaceState(null, "", "#" + pid); } catch (e) {}
    document.querySelectorAll("[data-pid]").forEach(function (el) { el.classList.toggle("activa", el.dataset.pid === pid); });
    var s = $("jugador"); s.hidden = false; s.style.borderTop = "6px solid " + p.color;
    $("j-titulo").textContent = "Tu informe · " + pid;
    $("j-sub").textContent = lugar(p) + " · visible el " + fmt(p.cobertura) + "% del partido";
    $("j-logros").innerHTML = (D.logros[pid] || []).map(function (b) { return logroHTML(b); }).join("");
    $("j-tiles").innerHTML =
      tile(fmt(p.distancia_m, 0) + " m", "Distancia recorrida") +
      tile(fmt(p.vel_punta_kmh) + " km/h", "Velocidad punta") +
      tile(fmt(p.zonas.red, 0) + "%", "Tiempo en la red") +
      tile(fmt(p.m_min, 0), "Metros por minuto");
    $("j-bar").innerHTML = ZONAS.map(function (z) { return '<div style="width:' + p.zonas[z[0]] + "%;background:" + z[2] + '"></div>'; }).join("");
    $("j-leyenda").innerHTML = ZONAS.map(function (z) { return "<span><i style=\"background:" + z[2] + "\"></i>" + z[1] + " " + fmt(p.zonas[z[0]], 0) + "%</span>"; }).join("");
    $("j-mapa").innerHTML = p.mapa ? '<img src="' + p.mapa + '" alt="Mapa de calor de ' + pid + '">' : "";
    var extra = p.cortado > 10 ? '<p class="nota">La cámara no ve el fondo de tu campo: el ' + fmt(p.cortado, 0) + "% del tiempo saliste cortado y ese recorrido no cuenta.</p>" : "";
    $("j-texto").innerHTML = (p.texto || "") + extra;
    if (scroll) s.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  // Resumen del partido
  var total = D.jugadores.reduce(function (a, p) { return a + p.distancia_m; }, 0);
  var rapido = D.jugadores.reduce(function (a, p) { return p.vel_punta_kmh > a.vel_punta_kmh ? p : a; }, D.jugadores[0] || { vel_punta_kmh: 0 });
  $("p-tiles").innerHTML =
    tile(min >= 1 ? fmt(min, 0) + " min" : fmt(D.duracion_s, 0) + " s", "Tiempo analizado") +
    tile(fmt(total, 0) + " m", "Metros entre los 4") +
    tile(fmt(rapido.vel_punta_kmh) + " km/h", "Punta más rápida (" + (rapido.id || "-") + ")") +
    tile(String(D.jugadores.length), "Jugadores");
  $("p-resumen").innerHTML = D.resumen_html || "";
  var todos = [];
  Object.keys(D.logros).forEach(function (pid) { D.logros[pid].forEach(function (b) { todos.push(logroHTML(b, pid)); }); });
  $("p-logros").innerHTML = todos.join("");
  $("p-parejas").innerHTML = D.parejas.map(function (q) {
    var who = q.jugadores.map(function (id) { return '<span class="punto" style="background:' + byId[id].color + '"></span>' + id; }).join(" y ");
    return '<div class="pareja"><div><b>' + who + "</b><div class=\"muted\">Campo " + (q.campo === "cerca" ? "cercano" : "lejano") + "</div></div>" +
      '<div class="nums">Juntos en la red ' + fmt(q.red, 0) + "%<br>Juntos en el fondo " + fmt(q.fondo, 0) + "%<br>Desalineados " + fmt(q.desalineados, 0) + "%</div></div>";
  }).join("") + (D.parejas_html ? '<div class="texto">' + D.parejas_html + "</div>" : "");

  $("aviso-ia").textContent = D.con_ia
    ? "Este informe se ha generado con inteligencia artificial a partir del vídeo. Las cifras son estimaciones."
    : "Informe automático generado a partir del vídeo. Las cifras son estimaciones.";
  $("limitaciones").innerHTML = D.limitaciones.map(function (l) { return "<li>" + esc(l) + "</li>"; }).join("");

  // Imagen para compartir (se dibuja en el móvil)
  function cargar(src) { return new Promise(function (ok) { if (!src) return ok(null); var i = new Image(); i.onload = function () { ok(i); }; i.onerror = function () { ok(null); }; i.src = src; }); }
  function rrect(ctx, x, y, w, h, r) { ctx.beginPath(); ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r); ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath(); }
  $("compartir").addEventListener("click", function () {
    if (!actual) return;
    var p = byId[actual], nombre = ($("nombre").value || "").trim() || p.id;
    var cv = $("lienzo"), ctx = cv.getContext("2d");
    cargar(p.mapa).then(function (mapa) {
      var g = ctx.createLinearGradient(0, 0, 1080, 1350); g.addColorStop(0, "#0b3d91"); g.addColorStop(1, "#061a40");
      ctx.fillStyle = g; ctx.fillRect(0, 0, 1080, 1350);
      ctx.fillStyle = "rgba(255,255,255,.75)"; ctx.font = "600 34px system-ui, sans-serif"; ctx.fillText("MI PARTIDO DE PÁDEL", 72, 120);
      ctx.fillStyle = "#fff"; ctx.font = "800 96px system-ui, sans-serif"; ctx.fillText(nombre, 72, 225, 936);
      ctx.fillStyle = p.color; ctx.fillRect(72, 252, 140, 10);
      var b = (D.logros[p.id] || [])[0];
      if (b) { ctx.fillStyle = "rgba(255,255,255,.12)"; rrect(ctx, 72, 300, 936, 96, 48); ctx.fill(); ctx.fillStyle = "#fff"; ctx.font = "700 44px system-ui, sans-serif"; ctx.fillText(b.icono + "  " + b.titulo, 112, 364, 860); }
      var stats = [[fmt(p.distancia_m, 0) + " m", "recorridos"], [fmt(p.vel_punta_kmh) + " km/h", "velocidad punta"], [fmt(p.zonas.red, 0) + "%", "en la red"], [fmt(p.m_min, 0), "metros por minuto"]];
      stats.forEach(function (s, i) {
        var y = 500 + i * 190;
        ctx.fillStyle = "#fff"; ctx.font = "800 84px system-ui, sans-serif"; ctx.fillText(s[0], 72, y, 560);
        ctx.fillStyle = "rgba(255,255,255,.7)"; ctx.font = "500 36px system-ui, sans-serif"; ctx.fillText(s[1], 72, y + 52);
      });
      if (mapa) { var h = 760, w = h * mapa.width / mapa.height; ctx.save(); rrect(ctx, 1008 - w, 440, w, h, 24); ctx.clip(); ctx.drawImage(mapa, 1008 - w, 440, w, h); ctx.restore(); }
      ctx.fillStyle = "rgba(255,255,255,.6)"; ctx.font = "500 30px system-ui, sans-serif"; ctx.fillText("Análisis de pádel con IA", 72, 1290);
      var a = document.createElement("a"); a.download = "mi-partido-" + p.id + ".png"; a.href = cv.toDataURL("image/png"); document.body.appendChild(a); a.click(); a.remove();
    });
  });

  var inicial = (location.hash || "").slice(1);
  if (byId[inicial]) elegir(inicial, false);
})();
</script>
</body>
</html>
"""

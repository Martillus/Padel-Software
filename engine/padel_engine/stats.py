"""Estadísticas por jugador y por pareja a partir de las trayectorias en metros."""

from __future__ import annotations

from collections import Counter

import numpy as np

from .ball import HitCandidate
from .court import COURT_LENGTH, COURT_WIDTH, NET_Y, side_of, zone_of
from .tracking import Track, smooth_track

HEATMAP_CELL_M = 0.5
MAX_HUMAN_SPEED = 8.0  # m/s; por encima es ruido de detección
MAX_DT_FOR_DISTANCE = 0.5  # s; huecos mayores no cuentan como recorrido
SPRINT_SPEED = 3.0  # m/s
SPRINT_MIN_S = 0.4


def _speeds(t: np.ndarray, xy: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Devuelve (dt, distancia por tramo, velocidad por tramo) solo de tramos válidos."""
    if len(t) < 2:
        return np.zeros(0), np.zeros(0), np.zeros(0)
    dt = np.diff(t)
    d = np.linalg.norm(np.diff(xy, axis=0), axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        v = np.where(dt > 0, d / dt, 0.0)
    valid = (dt > 0) & (dt <= MAX_DT_FOR_DISTANCE) & (v <= MAX_HUMAN_SPEED)
    return np.where(valid, dt, 0.0), np.where(valid, d, 0.0), np.where(valid, v, 0.0)


def heatmap_grid(xy: np.ndarray) -> np.ndarray:
    """Fracción de tiempo en cada celda de 0,5 m x 0,5 m (filas = eje y, columnas = eje x)."""
    nx, ny = int(COURT_WIDTH / HEATMAP_CELL_M), int(COURT_LENGTH / HEATMAP_CELL_M)
    if len(xy) == 0:
        return np.zeros((ny, nx))
    clipped = np.clip(xy, [0, 0], [COURT_WIDTH - 1e-6, COURT_LENGTH - 1e-6])
    grid, _, _ = np.histogram2d(
        clipped[:, 1], clipped[:, 0], bins=[ny, nx], range=[[0, COURT_LENGTH], [0, COURT_WIDTH]]
    )
    return grid / grid.sum()


def _sprints(t: np.ndarray, v: np.ndarray) -> list[dict]:
    """Tramos continuos por encima de SPRINT_SPEED (aceleraciones/desplazamientos explosivos)."""
    out, start = [], None
    for i, speed in enumerate(v):
        if speed >= SPRINT_SPEED and start is None:
            start = i
        elif speed < SPRINT_SPEED and start is not None:
            if t[i] - t[start] >= SPRINT_MIN_S:
                out.append({"inicio_s": round(float(t[start]), 2), "fin_s": round(float(t[i]), 2), "vel_max_mps": round(float(v[start:i].max()), 2)})
            start = None
    if start is not None and t[-1] - t[start] >= SPRINT_MIN_S:
        out.append({"inicio_s": round(float(t[start]), 2), "fin_s": round(float(t[-1]), 2), "vel_max_mps": round(float(v[start:].max()), 2)})
    return out


def player_stats(track: Track, analyzed_duration_s: float, hits: list[HitCandidate]) -> dict:
    t, xy_raw, _ = track.arrays()
    xy = smooth_track(t, xy_raw)
    dt, d, v = _speeds(t, xy)

    observed_s = float(dt.sum())
    zones = Counter(zone_of(p[1]) for p in xy)
    sides = Counter(side_of(p[1]) for p in xy)
    n = max(len(xy), 1)
    moving_v = v[v > 0.3]
    my_hits = [h for h in hits if h.player_id == track.track_id]
    sprints = _sprints(t[1:], v) if len(v) else []

    return {
        "id": track.track_id,
        "campo": sides.most_common(1)[0][0] if sides else None,
        "lado_habitual": "izquierda" if np.median(xy[:, 0]) < COURT_WIDTH / 2 else "derecha",
        "tiempo_visible_s": round(observed_s, 1),
        "cobertura_pct": round(100 * observed_s / analyzed_duration_s, 1) if analyzed_duration_s else 0.0,
        "distancia_m": round(float(d.sum()), 1),
        "velocidad_media_en_movimiento_mps": round(float(moving_v.mean()), 2) if len(moving_v) else 0.0,
        "velocidad_punta_mps": round(float(np.percentile(v, 98)), 2) if len(v) else 0.0,
        "metros_por_minuto": round(float(d.sum()) / (observed_s / 60), 1) if observed_s > 0 else 0.0,
        "zonas_pct": {z: round(100 * zones.get(z, 0) / n, 1) for z in ("red", "transicion", "fondo")},
        "distancia_media_a_red_m": round(float(np.mean(np.abs(xy[:, 1] - NET_Y))), 2),
        "posicion_media": {"x": round(float(xy[:, 0].mean()), 2), "y": round(float(xy[:, 1].mean()), 2)},
        "sprints": {"num": len(sprints), "top": sorted(sprints, key=lambda s: -s["vel_max_mps"])[:3]},
        "golpes_estimados": {
            "num": len(my_hits),
            "por_zona": dict(Counter(zone_of(h.court_xy[1]) for h in my_hits)),
            "fiabilidad": "experimental",
        },
        "_heatmap": heatmap_grid(xy),
        "_trayectoria": xy,
        "_t": t,
    }


def pair_stats(tracks: list[Track]) -> list[dict]:
    """Métricas tácticas de pareja (dos jugadores en el mismo campo).

    "Desalineados" = uno en la red y otro en el fondo a la vez: es uno de los errores
    tácticos más típicos en pádel y se puede medir solo con posiciones.
    """
    by_side: dict[str, list[Track]] = {}
    for tr in tracks:
        _, xy, _ = tr.arrays()
        by_side.setdefault(side_of(float(np.median(xy[:, 1]))), []).append(tr)

    out = []
    for side, trs in by_side.items():
        if len(trs) != 2:
            continue
        a, b = trs
        pa = {o.frame: o.court_xy for o in a.observations}
        pb = {o.frame: o.court_xy for o in b.observations}
        common = sorted(set(pa) & set(pb))
        if len(common) < 5:
            continue
        A = np.array([pa[f] for f in common])
        B = np.array([pb[f] for f in common])
        za = np.array([zone_of(y) for y in A[:, 1]])
        zb = np.array([zone_of(y) for y in B[:, 1]])
        both_net = np.mean((za == "red") & (zb == "red"))
        both_back = np.mean((za == "fondo") & (zb == "fondo"))
        split = np.mean(((za == "red") & (zb == "fondo")) | ((za == "fondo") & (zb == "red")))
        out.append(
            {
                "campo": side,
                "jugadores": [a.track_id, b.track_id],
                "fotogramas_comunes": len(common),
                "ambos_en_red_pct": round(100 * float(both_net), 1),
                "ambos_en_fondo_pct": round(100 * float(both_back), 1),
                "desalineados_pct": round(100 * float(split), 1),
                "distancia_media_entre_ellos_m": round(float(np.mean(np.linalg.norm(A - B, axis=1))), 2),
                "desfase_profundidad_medio_m": round(float(np.mean(np.abs(A[:, 1] - B[:, 1]))), 2),
            }
        )
    return out

"""Bola y golpes — EXPERIMENTAL.

Realidad técnica: la bola de pádel es pequeña, rápida y sale borrosa en un vídeo de
móvil. Un detector genérico (COCO "sports ball") la pierde muy a menudo. Para hacerlo
bien hará falta un modelo específico tipo TrackNet entrenado con vídeos reales nuestros
(ver docs/HOJA_DE_RUTA.md). Mientras tanto:

* Guardamos las detecciones de bola que haya.
* Estimamos "golpes candidatos": momentos en que la bola cambia de dirección cerca de
  un jugador. Sirve para contar golpes aproximados y saber desde qué zona golpea cada
  alumno, NO para clasificar el tipo de golpe (bandeja, víbora, globo...).

En los entrenamientos suele haber muchas bolas por el suelo: se descartan las que no se
mueven.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .detection import Detection
from .tracking import Track


@dataclass
class HitCandidate:
    frame: int
    t: float
    player_id: str
    court_xy: tuple[float, float]


def _moving_ball_detections(balls: list[Detection], min_move_px: float = 4.0) -> list[Detection]:
    """Una bola por fotograma (la más fiable) y solo si se mueve respecto al fotograma anterior."""
    best: dict[int, Detection] = {}
    for b in balls:
        if b.frame not in best or b.conf > best[b.frame].conf:
            best[b.frame] = b
    frames = sorted(best)
    out: list[Detection] = []
    for prev, cur in zip(frames, frames[1:]):
        a, b = best[prev].center, best[cur].center
        if np.hypot(a[0] - b[0], a[1] - b[1]) >= min_move_px:
            out.append(best[cur])
    return out


def detect_hit_candidates(
    balls: list[Detection],
    tracks: list[Track],
    fps: float,
    max_gap_frames: int = 6,
    min_separation_s: float = 0.6,
) -> list[HitCandidate]:
    moving = _moving_ball_detections(balls)
    if len(moving) < 3:
        return []

    obs_by_frame: dict[int, list[tuple[str, object]]] = {}
    for tr in tracks:
        for ob in tr.observations:
            obs_by_frame.setdefault(ob.frame, []).append((tr.track_id, ob))

    hits: list[HitCandidate] = []
    for a, b, c in zip(moving, moving[1:], moving[2:]):
        if c.frame - a.frame > max_gap_frames:
            continue
        vy1 = b.center[1] - a.center[1]
        vy2 = c.center[1] - b.center[1]
        vx1 = b.center[0] - a.center[0]
        vx2 = c.center[0] - b.center[0]
        reversed_dir = (vy1 * vy2 < 0) or (vx1 * vx2 < 0 and abs(vx1) > 3 and abs(vx2) > 3)
        if not reversed_dir:
            continue
        # ¿Hay un jugador cuya caja (ampliada) contenga la bola en ese momento?
        bx, by = b.center
        best_id, best_ob, best_d = None, None, 1e9
        for f in range(b.frame - 2, b.frame + 3):
            for pid, ob in obs_by_frame.get(f, []):
                x1, y1, x2, y2 = ob.bbox
                w, h = x2 - x1, y2 - y1
                if x1 - 0.6 * w <= bx <= x2 + 0.6 * w and y1 - 0.5 * h <= by <= y2:
                    d = np.hypot(bx - (x1 + x2) / 2, by - (y1 + y2) / 2)
                    if d < best_d:
                        best_id, best_ob, best_d = pid, ob, d
        if best_id is None:
            continue
        t = b.frame / fps
        if hits and hits[-1].player_id == best_id and t - hits[-1].t < min_separation_s:
            continue
        hits.append(HitCandidate(frame=b.frame, t=t, player_id=best_id, court_xy=best_ob.court_xy))
    return hits

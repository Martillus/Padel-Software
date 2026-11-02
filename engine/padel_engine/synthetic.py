"""Vídeo sintético de prueba con "verdad conocida".

Sirve para comprobar de punta a punta la calibración, el seguimiento, las estadísticas y
el informe sin depender de un modelo de visión ni de vídeos reales. Genera:

* ``sintetico.mp4``       – vídeo 1280x720 visto desde detrás de la pista
* ``calibracion.json``    – puntos de la pista en la imagen
* ``detecciones.json``    – detecciones "perfectas con ruido" (para el detector replay)
* ``verdad.json``         – trayectorias reales, para medir el error del pipeline
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import cv2
import numpy as np

from .court import COURT_LINES, KEYPOINTS, CourtHomography
from .detection import BALL, PERSON, Detection

W, H = 1280, 720
# Dónde caen las esquinas de la pista en una grabación típica de móvil desde detrás.
CAMERA_POINTS = {
    "near_left": (140.0, 690.0),
    "near_right": (1140.0, 690.0),
    "far_left": (455.0, 170.0),
    "far_right": (825.0, 170.0),
}


def _camera() -> CourtHomography:
    return CourtHomography.from_points(CAMERA_POINTS)


def _player_paths(duration_s: float, fps: float, rng: np.random.Generator) -> dict[str, np.ndarray]:
    """4 jugadores: pareja cercana bastante alineada, pareja lejana a menudo desalineada."""
    t = np.arange(0, duration_s, 1 / fps)
    slow = lambda f, ph: np.sin(2 * np.pi * f * t + ph)  # noqa: E731
    paths = {
        # (x, y) en metros
        "A": np.c_[2.6 + 0.9 * slow(0.11, 0.0), 5.5 + 3.0 * slow(0.05, 0.0)],
        "B": np.c_[7.4 + 0.9 * slow(0.13, 1.0), 5.5 + 3.0 * slow(0.05, 0.3)],
        "C": np.c_[2.6 + 1.0 * slow(0.12, 2.0), 12.2 + 0.8 * slow(0.07, 0.5)],  # casi siempre en red
        "D": np.c_[7.4 + 1.0 * slow(0.10, 3.0), 17.5 + 1.2 * slow(0.06, 1.5)],  # casi siempre en fondo
    }
    for k in paths:
        paths[k] = paths[k] + rng.normal(0, 0.02, paths[k].shape)
    return {k: np.clip(v, [0.2, 0.2], [9.8, 19.8]) for k, v in paths.items()}


def _bbox_for(hom: CourtHomography, x: float, y: float) -> tuple[float, float, float, float]:
    """Caja aproximada de una persona de 1,8 m usando la escala local de la perspectiva."""
    foot = hom.court_to_image(np.array([[x, y]]))[0]
    side = hom.court_to_image(np.array([[x + 0.6, y]]))[0]
    px_per_m = abs(side[0] - foot[0]) / 0.6
    h = 1.8 * px_per_m * 1.15
    w = 0.6 * px_per_m
    return (foot[0] - w / 2, foot[1] - h, foot[0] + w / 2, foot[1])


def generate(out_dir: str | Path, duration_s: float = 40.0, fps: float = 30.0, seed: int = 7) -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    hom = _camera()
    paths = _player_paths(duration_s, fps, rng)
    n = len(next(iter(paths.values())))

    # Bola: va y viene entre un jugador cercano y uno lejano cada ~1,2 s.
    hitters = ["A", "C", "B", "D"]
    seg = int(1.2 * fps)

    writer = cv2.VideoWriter(str(out_dir / "sintetico.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), fps, (W, H))
    detections: list[Detection] = []
    colors = {"A": (0, 200, 255), "B": (60, 60, 230), "C": (80, 220, 80), "D": (220, 120, 220)}
    for i in range(n):
        img = np.full((H, W, 3), (70, 110, 60), np.uint8)
        poly = hom.court_to_image(np.array([[0, 0], [10, 0], [10, 20], [0, 20]])).astype(np.int32)
        cv2.fillPoly(img, [poly], (170, 100, 40))
        for a, b in COURT_LINES:
            pa, pb = hom.court_to_image(np.array([a, b])).astype(int)
            cv2.line(img, tuple(pa), tuple(pb), (255, 255, 255), 2)
        # Dibujamos de lejos a cerca para que los cercanos tapen a los lejanos.
        for pid in sorted(paths, key=lambda k: -paths[k][i, 1]):
            x, y = paths[pid][i]
            x1, y1, x2, y2 = _bbox_for(hom, x, y)
            cv2.rectangle(img, (int(x1), int(y1)), (int(x2), int(y2)), colors[pid], -1)
            jitter = rng.normal(0, 1.5, 4)
            detections.append(Detection(i, PERSON, *(np.array([x1, y1, x2, y2]) + jitter).tolist(), float(rng.uniform(0.6, 0.95))))
        # Bola entre dos golpeadores (interpolación en imagen a la altura del pecho)
        k = (i // seg) % len(hitters)
        src, dst = hitters[k], hitters[(k + 1) % len(hitters)]
        u = (i % seg) / seg
        bs = _bbox_for(hom, *paths[src][i])
        bd = _bbox_for(hom, *paths[dst][i])
        p0 = np.array([(bs[0] + bs[2]) / 2, bs[1] + 0.35 * (bs[3] - bs[1])])
        p1 = np.array([(bd[0] + bd[2]) / 2, bd[1] + 0.35 * (bd[3] - bd[1])])
        ball = p0 + (p1 - p0) * u - np.array([0, 120 * np.sin(np.pi * u)])
        if rng.random() < 0.7:  # la bola se pierde a menudo, como en la realidad
            cv2.circle(img, tuple(ball.astype(int)), 5, (0, 255, 255), -1)
            detections.append(Detection(i, BALL, ball[0] - 5, ball[1] - 5, ball[0] + 5, ball[1] + 5, 0.5))
        writer.write(img)
    writer.release()

    # Calibración "marcada a mano": 6 puntos visibles con ~1 px de error de clic.
    names = ("near_service_left", "near_service_right", "net_left", "net_right", "far_left", "far_right")
    img_pts = hom.court_to_image(np.array([KEYPOINTS[k] for k in names]))
    noisy = {k: (float(p[0] + rng.normal(0, 1.0)), float(p[1] + rng.normal(0, 1.0))) for k, p in zip(names, img_pts)}
    (out_dir / "calibracion.json").write_text(
        json.dumps({"frame_index": 0, "frame_size": [W, H], "image_points": {k: [round(a, 1), round(b, 1)] for k, (a, b) in noisy.items()}}, indent=2),
        encoding="utf-8",
    )
    (out_dir / "detecciones.json").write_text(json.dumps({"detections": [asdict(d) for d in detections]}), encoding="utf-8")
    truth = {k: v.tolist() for k, v in paths.items()}
    (out_dir / "verdad.json").write_text(json.dumps({"fps": fps, "trayectorias": truth}), encoding="utf-8")
    return {"video": out_dir / "sintetico.mp4", "calibracion": out_dir / "calibracion.json", "detecciones": out_dir / "detecciones.json", "verdad": out_dir / "verdad.json"}

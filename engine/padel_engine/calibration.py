"""Calibración de la pista: guardar/cargar los puntos marcados y una herramienta para marcarlos.

Decisión de producto: en vez de detectar las líneas automáticamente (frágil con vídeos de
móvil, cristales, sombras y redes), el entrenador marca 4-6 puntos de la pista en un
fotograma. Le lleva ~15 segundos y, como el móvil suele ponerse siempre en el mismo sitio,
la calibración se puede reutilizar entre vídeos de la misma pista. La detección automática
queda como mejora futura.
"""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

from .court import KEYPOINT_LABELS_ES, KEYPOINTS, CourtHomography, draw_court_overlay


def load_calibration(path: str | Path) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if "image_points" not in data:
        raise ValueError("El fichero de calibración debe tener la clave 'image_points'.")
    data["image_points"] = {k: tuple(v) for k, v in data["image_points"].items()}
    return data


def save_calibration(path: str | Path, image_points: dict, frame_size: tuple[int, int], frame_index: int) -> None:
    payload = {
        "frame_index": frame_index,
        "frame_size": list(frame_size),
        "image_points": {k: [round(float(v[0]), 1), round(float(v[1]), 1)] for k, v in image_points.items()},
    }
    Path(path).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def read_frame(video_path: str | Path, frame_index: int = 0) -> np.ndarray:
    cap = cv2.VideoCapture(str(video_path))
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
    ok, frame = cap.read()
    cap.release()
    if not ok:
        raise RuntimeError(f"No se pudo leer el fotograma {frame_index} de {video_path}")
    return frame


def export_calibration_frame(video_path: str | Path, out_png: str | Path, frame_index: int = 0) -> Path:
    """Guarda un fotograma con una rejilla de coordenadas para marcar los puntos a mano."""
    frame = read_frame(video_path, frame_index)
    h, w = frame.shape[:2]
    grid = frame.copy()
    step = 100
    for x in range(0, w, step):
        cv2.line(grid, (x, 0), (x, h), (255, 255, 255), 1)
        cv2.putText(grid, str(x), (x + 2, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
    for y in range(0, h, step):
        cv2.line(grid, (0, y), (w, y), (255, 255, 255), 1)
        cv2.putText(grid, str(y), (2, y - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
    frame = cv2.addWeighted(frame, 0.7, grid, 0.3, 0)
    cv2.imwrite(str(out_png), frame)
    return Path(out_png)


def interactive_calibration(video_path: str | Path, out_json: str | Path, frame_index: int = 0) -> dict:
    """Herramienta de escritorio: muestra el fotograma y pide clicar los puntos uno a uno.

    Usa matplotlib (funciona en Windows/Mac/Linux con escritorio). Para saltar un punto que
    no se ve, pulsa clic derecho o Enter sin clicar. En la web (fase 2) esto será un
    componente donde el entrenador arrastra 4 marcadores.
    """
    import matplotlib.pyplot as plt

    frame = read_frame(video_path, frame_index)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    points: dict[str, tuple[float, float]] = {}
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.imshow(rgb)
    for name in KEYPOINTS:
        ax.set_title(f"Clica: {KEYPOINT_LABELS_ES[name]}  (clic derecho / Enter = no se ve, saltar)")
        fig.canvas.draw()
        clicks = plt.ginput(1, timeout=0, mouse_add=1, mouse_pop=None, mouse_stop=3)
        if clicks:
            x, y = clicks[0]
            points[name] = (x, y)
            ax.plot(x, y, "r+", markersize=14)
            ax.annotate(name, (x, y), color="yellow", fontsize=8)
    plt.close(fig)
    if len(points) < 4:
        raise RuntimeError("Se necesitan al menos 4 puntos.")
    h, w = frame.shape[:2]
    save_calibration(out_json, points, (w, h), frame_index)
    return load_calibration(out_json)


def calibration_check_image(frame: np.ndarray, hom: CourtHomography, image_points: dict, out_png: str | Path) -> None:
    """Imagen de control: líneas de la pista proyectadas + puntos marcados.

    Si las líneas amarillas no coinciden con las de la pista real, la calibración está mal
    y todas las métricas en metros serán erróneas. Es lo primero que hay que revisar.
    """
    img = draw_court_overlay(frame, hom)
    for name, (x, y) in image_points.items():
        cv2.circle(img, (int(x), int(y)), 6, (0, 0, 255), -1)
        cv2.putText(img, name, (int(x) + 6, int(y) - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
    cv2.putText(
        img,
        f"Error de reproyeccion: {hom.reprojection_error_px:.1f}px",
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (0, 255, 255),
        2,
    )
    cv2.imwrite(str(out_png), img)

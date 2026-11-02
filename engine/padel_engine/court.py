"""Geometría de una pista de pádel reglamentaria y homografía imagen -> pista.

Sistema de coordenadas (en metros), visto desde la cámara situada DETRÁS de la pista:

    y = 20  +-----------------+   fondo lejano (far)
            |        |        |
    y=16.95 |--------+--------|   línea de saque lejana
            |                 |
    y = 10  |=================|   red
            |                 |
    y=3.05  |--------+--------|   línea de saque cercana
            |        |        |
    y = 0   +-----------------+   fondo cercano (near, lado de la cámara)
          x=0      x=5      x=10
        (izquierda)        (derecha)

La pista mide 10 m x 20 m. Las líneas de saque están a 6,95 m de la red.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

COURT_WIDTH = 10.0
COURT_LENGTH = 20.0
NET_Y = 10.0
SERVICE_LINE_DIST = 6.95  # distancia de la línea de saque a la red
NEAR_SERVICE_Y = NET_Y - SERVICE_LINE_DIST  # 3.05
FAR_SERVICE_Y = NET_Y + SERVICE_LINE_DIST  # 16.95

# Puntos con nombre que el entrenador (o la web) puede marcar en un fotograma.
# Basta con 4 puntos no alineados; con más, la homografía es más robusta.
KEYPOINTS: dict[str, tuple[float, float]] = {
    "near_left": (0.0, 0.0),
    "near_right": (COURT_WIDTH, 0.0),
    "near_service_left": (0.0, NEAR_SERVICE_Y),
    "near_service_center": (COURT_WIDTH / 2, NEAR_SERVICE_Y),
    "near_service_right": (COURT_WIDTH, NEAR_SERVICE_Y),
    "net_left": (0.0, NET_Y),
    "net_right": (COURT_WIDTH, NET_Y),
    "far_service_left": (0.0, FAR_SERVICE_Y),
    "far_service_center": (COURT_WIDTH / 2, FAR_SERVICE_Y),
    "far_service_right": (COURT_WIDTH, FAR_SERVICE_Y),
    "far_left": (0.0, COURT_LENGTH),
    "far_right": (COURT_WIDTH, COURT_LENGTH),
}

KEYPOINT_LABELS_ES: dict[str, str] = {
    "near_left": "Esquina fondo cercano izquierda",
    "near_right": "Esquina fondo cercano derecha",
    "near_service_left": "Línea de saque cercana, lateral izquierdo",
    "near_service_center": "Línea de saque cercana, centro (T)",
    "near_service_right": "Línea de saque cercana, lateral derecho",
    "net_left": "Poste de la red izquierdo (suelo)",
    "net_right": "Poste de la red derecho (suelo)",
    "far_service_left": "Línea de saque lejana, lateral izquierdo",
    "far_service_center": "Línea de saque lejana, centro (T)",
    "far_service_right": "Línea de saque lejana, lateral derecho",
    "far_left": "Esquina fondo lejano izquierda",
    "far_right": "Esquina fondo lejano derecha",
}

# Segmentos de líneas de la pista (para dibujar y verificar la calibración).
COURT_LINES: list[tuple[tuple[float, float], tuple[float, float]]] = [
    ((0, 0), (COURT_WIDTH, 0)),
    ((0, COURT_LENGTH), (COURT_WIDTH, COURT_LENGTH)),
    ((0, 0), (0, COURT_LENGTH)),
    ((COURT_WIDTH, 0), (COURT_WIDTH, COURT_LENGTH)),
    ((0, NET_Y), (COURT_WIDTH, NET_Y)),
    ((0, NEAR_SERVICE_Y), (COURT_WIDTH, NEAR_SERVICE_Y)),
    ((0, FAR_SERVICE_Y), (COURT_WIDTH, FAR_SERVICE_Y)),
    ((COURT_WIDTH / 2, NEAR_SERVICE_Y), (COURT_WIDTH / 2, FAR_SERVICE_Y)),
]


class CalibrationError(ValueError):
    pass


@dataclass
class CourtHomography:
    """Transforma píxeles de la imagen a metros sobre el suelo de la pista."""

    image_to_court: np.ndarray  # matriz 3x3
    reprojection_error_px: float

    @classmethod
    def from_points(cls, image_points: dict[str, tuple[float, float]]) -> "CourtHomography":
        unknown = set(image_points) - set(KEYPOINTS)
        if unknown:
            raise CalibrationError(f"Puntos desconocidos: {sorted(unknown)}. Válidos: {list(KEYPOINTS)}")
        if len(image_points) < 4:
            raise CalibrationError("Hacen falta al menos 4 puntos de la pista para calibrar.")
        names = list(image_points)
        src = np.array([image_points[n] for n in names], dtype=np.float64)
        dst = np.array([KEYPOINTS[n] for n in names], dtype=np.float64)
        method = cv2.RANSAC if len(names) > 4 else 0
        H, _ = cv2.findHomography(src, dst, method, 0.5)
        if H is None:
            raise CalibrationError("No se pudo calcular la homografía (¿puntos alineados o repetidos?).")
        hom = cls(image_to_court=H, reprojection_error_px=0.0)
        # Error de reproyección en píxeles: cuánto se desvían los puntos marcados.
        reproj = hom.court_to_image(dst)
        hom.reprojection_error_px = float(np.mean(np.linalg.norm(reproj - src, axis=1)))
        return hom

    @property
    def court_to_image_matrix(self) -> np.ndarray:
        return np.linalg.inv(self.image_to_court)

    def image_to_court_pts(self, pts: np.ndarray) -> np.ndarray:
        pts = np.asarray(pts, dtype=np.float64).reshape(-1, 1, 2)
        if len(pts) == 0:
            return np.zeros((0, 2))
        return cv2.perspectiveTransform(pts, self.image_to_court).reshape(-1, 2)

    def court_to_image(self, pts: np.ndarray) -> np.ndarray:
        pts = np.asarray(pts, dtype=np.float64).reshape(-1, 1, 2)
        if len(pts) == 0:
            return np.zeros((0, 2))
        return cv2.perspectiveTransform(pts, self.court_to_image_matrix).reshape(-1, 2)


def in_court(xy: np.ndarray, margin: float = 0.0) -> np.ndarray:
    """True si el punto está dentro de la pista ampliada con un margen (m)."""
    xy = np.atleast_2d(xy)
    return (
        (xy[:, 0] >= -margin)
        & (xy[:, 0] <= COURT_WIDTH + margin)
        & (xy[:, 1] >= -margin)
        & (xy[:, 1] <= COURT_LENGTH + margin)
    )


def zone_of(y: float) -> str:
    """Zona según la distancia a la red: 'red', 'transicion' o 'fondo'."""
    d = abs(y - NET_Y)
    if d <= 3.5:
        return "red"
    if d <= SERVICE_LINE_DIST:
        return "transicion"
    return "fondo"


def side_of(y: float) -> str:
    """Campo en el que está el jugador respecto a la cámara."""
    return "cerca" if y < NET_Y else "lejos"


def draw_court_overlay(frame: np.ndarray, hom: CourtHomography, color=(0, 255, 255)) -> np.ndarray:
    """Dibuja las líneas de la pista proyectadas sobre el fotograma (para verificar la calibración)."""
    out = frame.copy()
    for a, b in COURT_LINES:
        seg = np.linspace(a, b, 50)  # muchas muestras para que se vea bien aunque salga del encuadre
        img = hom.court_to_image(seg).astype(np.int32)
        cv2.polylines(out, [img.reshape(-1, 1, 2)], False, color, 2, cv2.LINE_AA)
    return out

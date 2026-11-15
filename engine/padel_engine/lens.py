"""Corrección de la distorsión de la lente (gran angular / "ojo de pez" suave).

Las cámaras de club suelen llevar lentes gran angular para ver la pista entera desde
cerca. Esas lentes curvan las líneas rectas (más cuanto más lejos del centro de la
imagen). Una homografía sola no puede representar curvas, y el error llega a metros.

Solución: modelo de distorsión radial estándar (el de OpenCV, coeficientes k1 y k2).
Lo calculamos a partir de puntos marcados A LO LARGO de líneas de la pista que sabemos
que son rectas (línea de saque, línea central, red...): buscamos los coeficientes que
las vuelven rectas. Se hace una vez por cámara y se guarda en la calibración.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import cv2
import numpy as np
from scipy.optimize import minimize


@dataclass
class LensModel:
    f: float  # focal en píxeles (fija = ancho de la imagen; k1/k2 absorben el resto)
    cx: float
    cy: float
    k1: float = 0.0
    k2: float = 0.0

    @property
    def K(self) -> np.ndarray:
        return np.array([[self.f, 0, self.cx], [0, self.f, self.cy], [0, 0, 1]], dtype=np.float64)

    @property
    def D(self) -> np.ndarray:
        return np.array([self.k1, self.k2, 0, 0, 0], dtype=np.float64)

    def undistort(self, pts: np.ndarray) -> np.ndarray:
        """Píxeles de la imagen real -> píxeles de una imagen "ideal" sin curvatura."""
        pts = np.asarray(pts, dtype=np.float64).reshape(-1, 1, 2)
        if len(pts) == 0:
            return np.zeros((0, 2))
        return cv2.undistortPoints(pts, self.K, self.D, P=self.K).reshape(-1, 2)

    def distort(self, pts: np.ndarray) -> np.ndarray:
        """Inverso: de la imagen ideal a la imagen real (para dibujar sobre el vídeo)."""
        pts = np.asarray(pts, dtype=np.float64).reshape(-1, 2)
        n = (pts - [self.cx, self.cy]) / self.f
        r2 = (n**2).sum(axis=1, keepdims=True)
        return n * (1 + self.k1 * r2 + self.k2 * r2**2) * self.f + [self.cx, self.cy]

    def scaled(self, sx: float, sy: float) -> "LensModel":
        return LensModel(self.f * sx, self.cx * sx, self.cy * sy, self.k1, self.k2)

    def to_dict(self) -> dict:
        return {k: round(v, 6) for k, v in asdict(self).items()}


def _straightness(lens: LensModel, lines: list[np.ndarray]) -> float:
    """Error cuadrático medio (px) de los puntos respecto a una recta, tras corregir la lente."""
    total, n = 0.0, 0
    for pts in lines:
        u = lens.undistort(pts)
        c = u - u.mean(axis=0)
        # La menor componente principal = desviación respecto a la mejor recta.
        s = np.linalg.svd(c, compute_uv=False)
        total += float(s[-1] ** 2)
        n += len(u)
    return float(np.sqrt(total / max(n, 1)))


def fit_lens(lines: list, frame_size: tuple[int, int]) -> tuple[LensModel, float, float]:
    """Calcula k1 y k2 para que las líneas marcadas queden rectas.

    Devuelve (modelo, error antes en px, error después en px).
    """
    w, h = frame_size
    arrays = [np.asarray(p, dtype=np.float64) for p in lines if len(p) >= 3]
    if not arrays:
        raise ValueError("Hacen falta al menos 3 puntos por línea para corregir la lente.")
    base = LensModel(f=float(w), cx=w / 2.0, cy=h / 2.0)
    before = _straightness(base, arrays)

    def cost(k):
        return _straightness(LensModel(base.f, base.cx, base.cy, k[0], k[1]), arrays)

    res = minimize(cost, x0=[0.0, 0.0], method="Nelder-Mead", options={"xatol": 1e-5, "fatol": 1e-4, "maxiter": 2000})
    lens = LensModel(base.f, base.cx, base.cy, float(res.x[0]), float(res.x[1]))
    return lens, before, _straightness(lens, arrays)

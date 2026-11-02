"""Movimiento de cámara y cambios de plano.

Problema: la calibración se hace sobre UN fotograma. Si la cámara se mueve (móvil en la
mano, trípode que se golpea, retransmisión que hace zoom) o cambia de plano (repetición,
primer plano), la calibración deja de encajar.

Solución: en cada fotograma buscamos "detalles fijos" (esquinas, letras de publicidad,
líneas, uniones del cristal) y los emparejamos con los del fotograma de calibración. Con
esas parejas calculamos cómo se ha movido la imagen (otra homografía) y corregimos.
Si casi no hay parejas, es que es otro plano: ese fotograma se descarta.

Los jugadores también tienen "detalles", pero se mueven; el método RANSAC los descarta
como valores atípicos porque no siguen el movimiento del resto de la imagen.

Comprobación extra: los gráficos fijos (marcador, logos de la cadena) coinciden aunque
el plano sea un primer plano. Por eso, además, comparamos el aspecto de la PISTA: se
"endereza" el fotograma actual y se compara con la pista del fotograma de calibración.
Si no se parecen, es otro plano.
"""

from __future__ import annotations

import cv2
import numpy as np


class CameraMotion:
    def __init__(
        self,
        reference_frame: np.ndarray,
        court_polygon: np.ndarray | None = None,
        work_width: int = 960,
        min_inliers: int = 60,
        n_features: int = 4000,
        min_similarity: float = 0.45,
    ):
        self.scale = work_width / reference_frame.shape[1]
        self.min_similarity = min_similarity
        self.orb = cv2.ORB_create(nfeatures=n_features, fastThreshold=10)
        self.matcher = cv2.BFMatcher(cv2.NORM_HAMMING)
        self.min_inliers = min_inliers
        self.ref_kp, self.ref_des = self._features(reference_frame)
        self.ref_gray = self._gray(reference_frame)
        self.court_mask = None
        if court_polygon is not None:
            self.court_mask = np.zeros(self.ref_gray.shape, np.uint8)
            cv2.fillPoly(self.court_mask, [np.int32(np.asarray(court_polygon) * self.scale)], 255)
        self.last: tuple[list, np.ndarray, np.ndarray] | None = None  # (kp, des, H a referencia)
        self.stats = {"validos": 0, "descartados": 0, "via_anterior": 0}

    def _gray(self, frame: np.ndarray) -> np.ndarray:
        small = cv2.resize(frame, None, fx=self.scale, fy=self.scale, interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        return cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)

    def _features(self, frame: np.ndarray, gray: np.ndarray | None = None):
        return self.orb.detectAndCompute(self._gray(frame) if gray is None else gray, None)

    def court_similarity(self, gray: np.ndarray, H_small: np.ndarray) -> float:
        """Parecido (correlación de bordes, -1..1) entre la pista de este fotograma y la de referencia."""
        if self.court_mask is None:
            return 1.0
        h, w = self.ref_gray.shape
        warped = cv2.warpPerspective(gray, H_small, (w, h))
        valid = cv2.warpPerspective(np.full(gray.shape, 255, np.uint8), H_small, (w, h))
        mask = (self.court_mask > 0) & (valid > 0)
        if mask.sum() < 0.3 * (self.court_mask > 0).sum():
            return 0.0  # gran parte de la pista queda fuera de la imagen
        e1 = cv2.GaussianBlur(cv2.Canny(warped, 50, 150), (9, 9), 0).astype(np.float32)[mask]
        e2 = cv2.GaussianBlur(cv2.Canny(self.ref_gray, 50, 150), (9, 9), 0).astype(np.float32)[mask]
        e1 -= e1.mean()
        e2 -= e2.mean()
        den = float(np.sqrt((e1**2).sum() * (e2**2).sum()))
        return float((e1 * e2).sum() / den) if den > 0 else 0.0

    def _match(self, kp, des, kp2, des2) -> tuple[np.ndarray | None, int]:
        if des is None or des2 is None or len(kp) < 8 or len(kp2) < 8:
            return None, 0
        pairs = self.matcher.knnMatch(des, des2, k=2)
        good = [m for m, *rest in pairs if rest and m.distance < 0.75 * rest[0].distance]
        if len(good) < self.min_inliers:
            return None, len(good)
        src = np.float32([kp[m.queryIdx].pt for m in good])
        dst = np.float32([kp2[m.trainIdx].pt for m in good])
        H, mask = cv2.findHomography(src, dst, cv2.RANSAC, 3.0)
        inliers = int(mask.sum()) if mask is not None else 0
        if H is None or inliers < self.min_inliers or not self._plausible(H):
            return None, inliers
        return H, inliers

    @staticmethod
    def _plausible(H: np.ndarray) -> bool:
        """Descarta transformaciones absurdas (espejos, zooms enormes)."""
        det = np.linalg.det(H[:2, :2])
        return 0.25 < det < 4.0 and abs(H[2, 0]) < 0.01 and abs(H[2, 1]) < 0.01

    def _to_full(self, H_small: np.ndarray) -> np.ndarray:
        S = np.diag([self.scale, self.scale, 1.0])
        return np.linalg.inv(S) @ H_small @ S

    def frame_to_reference(self, frame: np.ndarray) -> np.ndarray | None:
        """Matriz 3x3 que lleva píxeles de este fotograma al fotograma de calibración.

        Devuelve None si el fotograma es de otro plano (no se debe analizar).
        """
        gray = self._gray(frame)
        kp, des = self._features(frame, gray)
        H, _ = self._match(kp, des, self.ref_kp, self.ref_des)
        if H is None and self.last is not None:
            # Si el zoom ha cambiado mucho, quizá encaje mejor con el último fotograma bueno.
            lkp, ldes, lH = self.last
            H_prev, _ = self._match(kp, des, lkp, ldes)
            if H_prev is not None:
                H = lH @ H_prev
                if not self._plausible(H):
                    H = None
                else:
                    self.stats["via_anterior"] += 1
        if H is not None:
            self.last_similarity = self.court_similarity(gray, H)
            if self.last_similarity < self.min_similarity:
                H = None
        if H is None:
            self.stats["descartados"] += 1
            return None
        self.last = (kp, des, H)
        self.stats["validos"] += 1
        return self._to_full(H)

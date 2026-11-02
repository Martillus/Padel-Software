"""Seguimiento de jugadores en coordenadas de pista (metros).

Idea sencilla y robusta para pádel: sabemos cuántos jugadores hay (normalmente 4 en un
partido, 1-4 alumnos en un entrenamiento), así que mantenemos N "huecos" (J1..JN) y en
cada fotograma asignamos las detecciones al hueco más cercano en la pista (algoritmo
húngaro). Trabajar en metros en vez de píxeles hace que un jugador lejano (pequeño en
imagen) y uno cercano se traten igual.

Limitación conocida: si dos jugadores se cruzan muy pegados se pueden intercambiar las
etiquetas. Mitigación futura: apariencia (color de ropa, NO caras) y asignación manual
corrigiendo en la web.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import linear_sum_assignment

from .court import NET_Y


@dataclass
class PlayerObservation:
    frame: int
    t: float
    court_xy: tuple[float, float]
    bbox: tuple[float, float, float, float]
    conf: float


@dataclass
class Track:
    track_id: str
    observations: list[PlayerObservation] = field(default_factory=list)

    @property
    def last(self) -> PlayerObservation | None:
        return self.observations[-1] if self.observations else None

    def arrays(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        t = np.array([o.t for o in self.observations])
        xy = np.array([o.court_xy for o in self.observations]).reshape(-1, 2)
        fr = np.array([o.frame for o in self.observations])
        return t, xy, fr


class SlotTracker:
    def __init__(self, max_players: int = 4, max_speed_mps: float = 7.0, base_gate_m: float = 1.0, reacquire_after_s: float = 0.6):
        self.max_players = max_players
        self.max_speed = max_speed_mps
        self.base_gate = base_gate_m
        self.reacquire_after = reacquire_after_s
        self.tracks: list[Track] = []

    def _gate(self, dt: float) -> float:
        return self.base_gate + self.max_speed * min(dt, 2.0)

    def update(self, t: float, observations: list[PlayerObservation]) -> None:
        # Nos quedamos con las detecciones más fiables si hay más que huecos posibles.
        observations = sorted(observations, key=lambda o: -o.conf)[: self.max_players * 2]
        if not observations:
            return

        assigned_obs: set[int] = set()
        live = [tr for tr in self.tracks if tr.last is not None]
        if live:
            cost = np.zeros((len(live), len(observations)))
            for i, tr in enumerate(live):
                for j, ob in enumerate(observations):
                    d = np.hypot(tr.last.court_xy[0] - ob.court_xy[0], tr.last.court_xy[1] - ob.court_xy[1])
                    cost[i, j] = d if d <= self._gate(t - tr.last.t) else 1e6
            rows, cols = linear_sum_assignment(cost)
            for r, c in zip(rows, cols):
                if cost[r, c] < 1e6:
                    live[r].observations.append(observations[c])
                    assigned_obs.add(c)

        rest = [ob for j, ob in enumerate(observations) if j not in assigned_obs]
        for ob in rest:
            if len(self.tracks) < self.max_players:
                self.tracks.append(Track(track_id=f"J{len(self.tracks) + 1}", observations=[ob]))
                continue
            # Re-enganchar a un hueco que lleva un rato sin verse (oclusión, salió de plano...).
            # Preferimos un hueco del mismo campo (cerca/lejos) porque los jugadores rara vez cruzan la red.
            lost = [
                tr
                for tr in self.tracks
                if tr.last is not None and tr.last.t < t and (t - tr.last.t) >= self.reacquire_after
            ]
            if not lost:
                continue
            same_side = [tr for tr in lost if (tr.last.court_xy[1] < NET_Y) == (ob.court_xy[1] < NET_Y)]
            pool = same_side or lost
            best = min(pool, key=lambda tr: np.hypot(tr.last.court_xy[0] - ob.court_xy[0], tr.last.court_xy[1] - ob.court_xy[1]))
            best.observations.append(ob)

    def finalize(self, min_observations: int = 5) -> list[Track]:
        """Descarta huecos casi vacíos (falsos positivos) y renombra por posición.

        Nombres estables y fáciles de entender para el entrenador: se ordenan por campo
        (cerca primero) y de izquierda a derecha según su posición mediana.
        """
        good = [tr for tr in self.tracks if len(tr.observations) >= min_observations]

        def key(tr: Track):
            _, xy, _ = tr.arrays()
            med = np.median(xy, axis=0)
            return (0 if med[1] < NET_Y else 1, med[0])

        good.sort(key=key)
        for i, tr in enumerate(good, start=1):
            tr.track_id = f"J{i}"
        return good


def smooth_track(t: np.ndarray, xy: np.ndarray, window: int = 5) -> np.ndarray:
    """Suaviza la trayectoria (mediana deslizante) para quitar el temblor de las cajas."""
    if len(xy) < 3:
        return xy.copy()
    half = window // 2
    out = np.empty_like(xy)
    for i in range(len(xy)):
        lo, hi = max(0, i - half), min(len(xy), i + half + 1)
        out[i] = np.median(xy[lo:hi], axis=0)
    return out

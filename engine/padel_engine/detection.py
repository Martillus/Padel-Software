"""Detección de personas y bola en cada fotograma.

Los detectores son intercambiables (misma interfaz). Hoy hay tres:

* ``ultralytics``  – YOLO de Ultralytics. El más fácil y preciso para prototipar.
  ⚠️ LICENCIA AGPL-3.0: si se usa en el SaaS en producción hay que, o bien publicar el
  código del servicio, o bien comprar la licencia Enterprise de Ultralytics. Para el
  piloto/pruebas internas es aceptable; antes de cobrar hay que decidir (ver docs/DECISIONES.md).
* ``torchvision``  – Faster R-CNN de torchvision (licencia BSD, sin problemas comerciales).
  Más lento y algo menos preciso con jugadores lejanos.
* ``replay``       – Lee detecciones ya calculadas de un JSON (tests, vídeo sintético y
  para re-calcular estadísticas sin volver a pagar GPU).

Nada de reconocimiento facial: solo cajas de "persona" y "bola".
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol

import numpy as np

PERSON = "person"
BALL = "ball"


@dataclass
class Detection:
    frame: int
    cls: str  # "person" | "ball"
    x1: float
    y1: float
    x2: float
    y2: float
    conf: float

    @property
    def foot_point(self) -> tuple[float, float]:
        """Punto de apoyo en el suelo: centro del borde inferior de la caja."""
        return ((self.x1 + self.x2) / 2.0, self.y2)

    @property
    def center(self) -> tuple[float, float]:
        return ((self.x1 + self.x2) / 2.0, (self.y1 + self.y2) / 2.0)


class Detector(Protocol):
    name: str

    def detect(self, frame: np.ndarray, frame_index: int) -> list[Detection]: ...


class UltralyticsDetector:
    name = "ultralytics"
    COCO_PERSON, COCO_BALL = 0, 32

    def __init__(self, weights: str = "yolo11s.pt", conf: float = 0.25, device: str | None = None, imgsz: int = 1280):
        from ultralytics import YOLO

        self.model = YOLO(weights)
        self.conf = conf
        self.device = device
        # imgsz alto ayuda con los jugadores del fondo lejano (son pequeños en un vídeo de móvil).
        self.imgsz = imgsz

    def detect(self, frame: np.ndarray, frame_index: int) -> list[Detection]:
        res = self.model.predict(
            frame,
            conf=self.conf,
            classes=[self.COCO_PERSON, self.COCO_BALL],
            imgsz=self.imgsz,
            device=self.device,
            verbose=False,
        )[0]
        out: list[Detection] = []
        if res.boxes is None:
            return out
        for (x1, y1, x2, y2), c, k in zip(
            res.boxes.xyxy.cpu().numpy(), res.boxes.conf.cpu().numpy(), res.boxes.cls.cpu().numpy()
        ):
            cls = PERSON if int(k) == self.COCO_PERSON else BALL
            out.append(Detection(frame_index, cls, float(x1), float(y1), float(x2), float(y2), float(c)))
        return out


class TorchvisionDetector:
    name = "torchvision"
    COCO_PERSON, COCO_BALL = 1, 37  # índices de torchvision (con fondo en 0)

    def __init__(self, conf: float = 0.5, device: str | None = None):
        import torch
        from torchvision.models.detection import FasterRCNN_ResNet50_FPN_V2_Weights, fasterrcnn_resnet50_fpn_v2

        self.torch = torch
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        weights = FasterRCNN_ResNet50_FPN_V2_Weights.DEFAULT
        self.model = fasterrcnn_resnet50_fpn_v2(weights=weights).eval().to(self.device)
        self.conf = conf

    def detect(self, frame: np.ndarray, frame_index: int) -> list[Detection]:
        torch = self.torch
        rgb = frame[:, :, ::-1].copy()
        tensor = torch.from_numpy(rgb).permute(2, 0, 1).float().div(255).to(self.device)
        with torch.no_grad():
            pred = self.model([tensor])[0]
        out: list[Detection] = []
        for box, label, score in zip(pred["boxes"].cpu().numpy(), pred["labels"].cpu().numpy(), pred["scores"].cpu().numpy()):
            if score < self.conf or int(label) not in (self.COCO_PERSON, self.COCO_BALL):
                continue
            cls = PERSON if int(label) == self.COCO_PERSON else BALL
            out.append(Detection(frame_index, cls, *map(float, box), float(score)))
        return out


class ReplayDetector:
    """Devuelve detecciones guardadas previamente (``detections.json``)."""

    name = "replay"

    def __init__(self, path: str | Path):
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        items = raw["detections"] if isinstance(raw, dict) else raw
        self.by_frame: dict[int, list[Detection]] = {}
        for d in items:
            det = Detection(**d)
            self.by_frame.setdefault(det.frame, []).append(det)

    def detect(self, frame: np.ndarray, frame_index: int) -> list[Detection]:
        return list(self.by_frame.get(frame_index, []))


def build_detector(kind: str, **kwargs) -> Detector:
    if kind == "ultralytics":
        return UltralyticsDetector(**{k: v for k, v in kwargs.items() if k in ("weights", "conf", "device", "imgsz")})
    if kind == "torchvision":
        return TorchvisionDetector(**{k: v for k, v in kwargs.items() if k in ("conf", "device")})
    if kind == "replay":
        return ReplayDetector(kwargs["path"])
    raise ValueError(f"Detector desconocido: {kind}")


def save_detections(path: str | Path, detections: list[Detection]) -> None:
    Path(path).write_text(
        json.dumps({"detections": [asdict(d) for d in detections]}, ensure_ascii=False), encoding="utf-8"
    )

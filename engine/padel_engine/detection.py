"""Detección de personas y bola en cada fotograma.

Los detectores son intercambiables (misma interfaz). Hoy hay cuatro:

* ``yolox``        – YOLOX (Megvii) en formato ONNX. **Licencia Apache-2.0** (uso comercial
  sin problemas) y no necesita PyTorch: instalación ligera y contenedor de GPU más barato.
  Es el detector por defecto.
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
import logging
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol

import numpy as np

log = logging.getLogger(__name__)

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


YOLOX_URLS = {
    "yolox_s.onnx": "https://github.com/Megvii-BaseDetection/YOLOX/releases/download/0.1.1rc0/yolox_s.onnx",
    "yolox_m.onnx": "https://github.com/Megvii-BaseDetection/YOLOX/releases/download/0.1.1rc0/yolox_m.onnx",
    "yolox_l.onnx": "https://github.com/Megvii-BaseDetection/YOLOX/releases/download/0.1.1rc0/yolox_l.onnx",
}
MODELS_DIR = Path.home() / ".cache" / "padel_engine"


def _resolve_model(weights: str) -> Path:
    """Ruta local del modelo; si es uno conocido y no está, lo descarga (una sola vez)."""
    p = Path(weights)
    if p.exists():
        return p
    if p.name not in YOLOX_URLS:
        raise FileNotFoundError(f"No encuentro el modelo {weights}. Conocidos: {list(YOLOX_URLS)}")
    dest = MODELS_DIR / p.name
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        log.info("Descargando %s (solo la primera vez)...", p.name)
        tmp = dest.with_suffix(".part")
        urllib.request.urlretrieve(YOLOX_URLS[p.name], tmp)
        tmp.rename(dest)
    return dest


class YoloxDetector:
    """YOLOX en ONNX Runtime (CPU o GPU). Entrada fija de 640x640.

    Para que los jugadores del fondo lejano no salgan diminutos, se puede pasar ``roi``:
    se recorta la zona de la pista (más un margen) antes de detectar.
    """

    name = "yolox"
    COCO_PERSON, COCO_BALL = 0, 32
    SIZE = 640

    def __init__(self, weights: str = "yolox_m.onnx", conf: float = 0.25, device: str | None = None, nms: float = 0.45):
        import onnxruntime as ort

        providers = ["CPUExecutionProvider"]
        if device in (None, "cuda") and "CUDAExecutionProvider" in ort.get_available_providers():
            providers.insert(0, "CUDAExecutionProvider")
        self.session = ort.InferenceSession(str(_resolve_model(weights)), providers=providers)
        self.input_name = self.session.get_inputs()[0].name
        self.conf = conf
        self.nms = nms
        self.roi: tuple[int, int, int, int] | None = None  # x1, y1, x2, y2 en píxeles
        grids, strides = [], []
        for stride in (8, 16, 32):
            n = self.SIZE // stride
            xv, yv = np.meshgrid(np.arange(n), np.arange(n))
            grids.append(np.stack((xv, yv), 2).reshape(-1, 2))
            strides.append(np.full((n * n, 1), stride))
        self._grids = np.concatenate(grids).astype(np.float32)
        self._strides = np.concatenate(strides).astype(np.float32)

    def detect(self, frame: np.ndarray, frame_index: int) -> list[Detection]:
        import cv2

        ox, oy = 0, 0
        img = frame
        if self.roi is not None:
            x1, y1, x2, y2 = self.roi
            img = frame[y1:y2, x1:x2]
            ox, oy = x1, y1
        h, w = img.shape[:2]
        r = min(self.SIZE / h, self.SIZE / w)
        resized = cv2.resize(img, (int(w * r), int(h * r)), interpolation=cv2.INTER_LINEAR)
        padded = np.full((self.SIZE, self.SIZE, 3), 114, dtype=np.uint8)
        padded[: resized.shape[0], : resized.shape[1]] = resized
        blob = padded.transpose(2, 0, 1)[None].astype(np.float32)
        out = self.session.run(None, {self.input_name: blob})[0][0]

        xy = (out[:, :2] + self._grids) * self._strides
        wh = np.exp(out[:, 2:4]) * self._strides
        boxes = np.concatenate([xy - wh / 2, xy + wh / 2], axis=1) / r
        boxes[:, [0, 2]] += ox
        boxes[:, [1, 3]] += oy
        dets: list[Detection] = []
        for coco_id, cls in ((self.COCO_PERSON, PERSON), (self.COCO_BALL, BALL)):
            scores = out[:, 4] * out[:, 5 + coco_id]
            thr = self.conf if cls == PERSON else self.conf * 0.4  # la bola da puntuaciones bajas
            keep = np.where(scores > thr)[0]
            if not len(keep):
                continue
            b, sc = boxes[keep], scores[keep]
            idx = cv2.dnn.NMSBoxes([[float(x1), float(y1), float(x2 - x1), float(y2 - y1)] for x1, y1, x2, y2 in b], sc.tolist(), thr, self.nms)
            for i in np.array(idx).reshape(-1):
                dets.append(Detection(frame_index, cls, *map(float, b[i]), float(sc[i])))
        return dets


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
    if kind == "yolox":
        return YoloxDetector(**{k: v for k, v in kwargs.items() if k in ("weights", "conf", "device")})
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

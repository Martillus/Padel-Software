"""Pipeline completo: vídeo + calibración -> JSON de análisis, mapas de calor e informe."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import cv2
import numpy as np

from . import __version__
from .ball import detect_hit_candidates
from .calibration import calibration_check_image, load_calibration, read_frame
from .camera import CameraMotion
from .court import CourtHomography, in_court
from .detection import BALL, PERSON, Detection, Detector, build_detector, save_detections
from .heatmap import save_heatmap, save_trajectories
from .recommendations import pair_insights, player_insights
from .report import build_report
from .stats import pair_stats, player_stats
from .tracking import PlayerObservation, SlotTracker

log = logging.getLogger(__name__)

SCHEMA_VERSION = "0.1"


@dataclass
class PipelineConfig:
    detector: str = "yolox"
    weights: str | None = None  # por defecto: yolox_m.onnx (yolox) o yolo11s.pt (ultralytics)
    detections_path: str | None = None  # para detector "replay"
    device: str | None = None
    imgsz: int = 1280
    # Analizar 10 fotogramas por segundo en vez de 30/60 reduce el coste de GPU 3-6 veces
    # y para posiciones y recorridos es suficiente. La bola necesitaría más (fase posterior).
    analysis_fps: float = 10.0
    max_players: int = 4
    court_margin_m: float = 1.0
    min_person_conf: float = 0.3
    start_s: float = 0.0
    end_s: float | None = None
    annotated_video: bool = False
    # Corrige movimientos de cámara y descarta cambios de plano (repeticiones, primeros planos).
    stabilize: bool = True
    # Recorta la zona de la pista antes de detectar (jugadores lejanos más grandes para el modelo).
    court_roi: bool = True
    use_llm: bool = True
    context: dict = field(default_factory=dict)  # {"tipo_sesion": "partido"|"entrenamiento", "nivel": ...}
    player_names: dict = field(default_factory=dict)  # {"J1": "Lucía"} — nunca se envía a la IA


def _scale_points(points: dict, calib_size, video_size) -> dict:
    if not calib_size or tuple(calib_size) == tuple(video_size):
        return points
    sx, sy = video_size[0] / calib_size[0], video_size[1] / calib_size[1]
    log.warning("La calibración se hizo a %s y el vídeo es %s: escalo los puntos.", calib_size, video_size)
    return {k: (v[0] * sx, v[1] * sy) for k, v in points.items()}


def run_pipeline(video_path: str | Path, calibration_path: str | Path, out_dir: str | Path, cfg: PipelineConfig | None = None, detector: Detector | None = None) -> dict:
    cfg = cfg or PipelineConfig()
    video_path, out_dir = Path(video_path), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    timings: dict[str, float] = {}
    t0 = time.perf_counter()

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise FileNotFoundError(f"No se puede abrir el vídeo: {video_path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration = n_frames / fps if fps else 0.0

    calib = load_calibration(calibration_path)
    points = _scale_points(calib["image_points"], calib.get("frame_size"), (w, h))
    hom = CourtHomography.from_points(points)

    weights = cfg.weights or {"yolox": "yolox_m.onnx", "ultralytics": "yolo11s.pt"}.get(cfg.detector)
    if detector is None:
        detector = build_detector(
            cfg.detector, weights=weights, device=cfg.device, imgsz=cfg.imgsz, path=cfg.detections_path, conf=min(cfg.min_person_conf, 0.25)
        )
    ref_frame = read_frame(video_path, int(calib.get("frame_index", 0)))
    # Zona de la pista en el fotograma de calibración (con margen) para recortar antes de detectar.
    court_ref_poly = hom.court_to_image(np.array([[-1.5, -1.5], [11.5, -1.5], [11.5, 21.5], [-1.5, 21.5]]))
    court_floor = hom.court_to_image(np.array([[0, 0], [10, 0], [10, 20], [0, 20]]))
    camera = CameraMotion(ref_frame, court_polygon=court_floor) if cfg.stabilize else None
    timings["carga_s"] = time.perf_counter() - t0

    step = max(1, round(fps / cfg.analysis_fps))
    first = int(cfg.start_s * fps)
    last = min(n_frames, int(cfg.end_s * fps)) if cfg.end_s else n_frames
    tracker = SlotTracker(max_players=cfg.max_players)
    all_dets: list[Detection] = []
    balls: list[Detection] = []
    processed = 0
    valid = 0

    t1 = time.perf_counter()
    cap.set(cv2.CAP_PROP_POS_FRAMES, first)
    idx = first
    while idx < last:
        if (idx - first) % step != 0:
            if not cap.grab():
                break
            idx += 1
            continue
        ok, frame = cap.read()
        if not ok:
            break
        processed += 1
        H = np.eye(3)
        if camera is not None:
            H = camera.frame_to_reference(frame)
            if H is None:  # otro plano: no se analiza (y no se gasta GPU en él)
                idx += 1
                continue
        valid += 1
        if cfg.court_roi and hasattr(detector, "roi"):
            detector.roi = _roi_from_poly(court_ref_poly, np.linalg.inv(H), frame.shape)
        dets = detector.detect(frame, idx)
        all_dets.extend(dets)
        t = idx / fps
        persons = [d for d in dets if d.cls == PERSON and d.conf >= cfg.min_person_conf]
        balls.extend(d for d in dets if d.cls == BALL)
        if persons:
            feet = np.array([d.foot_point for d in persons])
            court_xy = hom.image_to_court_pts(_apply_h(H, feet))
            mask = in_court(court_xy, cfg.court_margin_m)
            obs = [
                PlayerObservation(idx, t, (float(c[0]), float(c[1])), (d.x1, d.y1, d.x2, d.y2), d.conf)
                for d, c, m in zip(persons, court_xy, mask)
                if m
            ]
            tracker.update(t, obs)
        idx += 1
    cap.release()
    timings["deteccion_s"] = time.perf_counter() - t1

    total_s = (min(idx, last) - first) / fps
    # Solo cuenta el tiempo con el plano bueno (sin repeticiones ni primeros planos).
    analyzed_s = total_s * (valid / processed) if processed else 0.0
    t2 = time.perf_counter()
    tracks = tracker.finalize()
    hits = detect_hit_candidates(balls, tracks, fps)

    players = []
    trajectories = {}
    for tr in tracks:
        p = player_stats(tr, analyzed_s, hits)
        p["observaciones"] = player_insights(p, analyzed_s)
        hm_png = save_heatmap(p["_heatmap"], out_dir / f"mapa_calor_{tr.track_id}.png", f"Mapa de calor {tr.track_id}")
        p["mapa_calor_png"] = hm_png.name
        p["mapa_calor_celdas"] = np.round(p["_heatmap"], 4).tolist()
        trajectories[tr.track_id] = p["_trayectoria"]
        players.append(p)
    pairs = pair_stats(tracks)
    for pair in pairs:
        pair["observaciones"] = pair_insights(pair, analyzed_s)
    if trajectories:
        save_trajectories(trajectories, out_dir / "recorridos.png")
    calibration_check_image(ref_frame, hom, points, out_dir / "calibracion_check.png")
    timings["estadisticas_s"] = time.perf_counter() - t2

    (out_dir / "trayectorias.json").write_text(
        json.dumps(
            {p["id"]: [[round(float(t), 2), round(float(x), 2), round(float(y), 2)] for t, (x, y) in zip(p["_t"], p["_trayectoria"])] for p in players}
        ),
        encoding="utf-8",
    )
    save_detections(out_dir / "detecciones.json", all_dets)

    limitations = [
        "Las posiciones se estiman con el punto de apoyo de cada jugador; con oclusiones o jugadores cortados por el borde del vídeo pueden desviarse ~0,5 m.",
        "Los golpes son estimaciones experimentales basadas en la bola, que se detecta de forma intermitente. No se clasifica el tipo de golpe todavía.",
        "Si dos jugadores se cruzan muy cerca, sus etiquetas pueden intercambiarse.",
    ]
    if hom.reprojection_error_px > 8:
        limitations.insert(0, f"Calibración imprecisa (error {hom.reprojection_error_px:.1f} px): revisa calibracion_check.png y el punto con más error: {max(hom.point_errors_px, key=hom.point_errors_px.get)}.")

    analysis = {
        "version_esquema": SCHEMA_VERSION,
        "motor": {"version": __version__, "detector": detector.name, "pesos": weights if detector.name in ("yolox", "ultralytics") else None},
        "video": {
            "archivo": video_path.name,
            "fps": round(fps, 2),
            "fotogramas": n_frames,
            "ancho": w,
            "alto": h,
            "duracion_s": round(duration, 2),
            "duracion_analizada_s": round(analyzed_s, 2),
            "fps_analisis": round(fps / step, 2),
            "fotogramas_procesados": processed,
            "fotogramas_validos": valid,
            "fotogramas_descartados_cambio_plano": processed - valid,
        },
        "calibracion": {
            "puntos": {k: [round(v[0], 1), round(v[1], 1)] for k, v in points.items()},
            "error_reproyeccion_px": round(hom.reprojection_error_px, 2),
            "error_por_punto_px": hom.point_errors_px,
        },
        "jugadores": [{k: v for k, v in p.items() if not k.startswith("_")} for p in players],
        "parejas": pairs,
        "golpes_estimados": [asdict(hit) | {"t": round(hit.t, 2)} for hit in hits],
        "detecciones": {"personas": sum(d.cls == PERSON for d in all_dets), "bolas": len(balls)},
        "limitaciones": limitations,
    }

    t3 = time.perf_counter()
    report_md, report_meta = build_report(analysis, use_llm=cfg.use_llm, context=cfg.context, names=cfg.player_names)
    (out_dir / "informe.md").write_text(report_md, encoding="utf-8")
    timings["informe_s"] = time.perf_counter() - t3
    analysis["informe"] = {"archivo": "informe.md", **report_meta}

    if cfg.annotated_video:
        t4 = time.perf_counter()
        _write_annotated(video_path, out_dir / "video_anotado.mp4", tracks, hom, fps / step, first, last, step)
        timings["video_anotado_s"] = time.perf_counter() - t4

    timings["total_s"] = time.perf_counter() - t0
    analysis["tiempos"] = {k: round(v, 2) for k, v in timings.items()}
    if analyzed_s > 0:
        # Útil para estimar el coste por vídeo: segundos de cómputo por minuto de vídeo.
        analysis["tiempos"]["segundos_computo_por_minuto_video"] = round(timings["deteccion_s"] / (analyzed_s / 60), 2)

    (out_dir / "analisis.json").write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")
    return analysis


def _apply_h(H: np.ndarray, pts: np.ndarray) -> np.ndarray:
    return cv2.perspectiveTransform(np.asarray(pts, dtype=np.float64).reshape(-1, 1, 2), H).reshape(-1, 2)


def _roi_from_poly(ref_poly: np.ndarray, ref_to_frame: np.ndarray, shape) -> tuple[int, int, int, int]:
    """Rectángulo que contiene la pista en este fotograma, con hueco arriba para el cuerpo de los jugadores lejanos."""
    h, w = shape[:2]
    poly = _apply_h(ref_to_frame, ref_poly)
    x1, y1 = poly.min(axis=0)
    x2, y2 = poly.max(axis=0)
    y1 -= 0.12 * h
    x1, y1 = max(0, int(x1)), max(0, int(y1))
    x2, y2 = min(w, int(x2)), min(h, int(y2))
    if x2 - x1 < w * 0.2 or y2 - y1 < h * 0.2:
        return (0, 0, w, h)
    return (x1, y1, x2, y2)


def _write_annotated(video_path: Path, out_path: Path, tracks, hom: CourtHomography, out_fps: float, first: int, last: int, step: int) -> None:
    """Vídeo de control con cajas, etiquetas y minimapa (para depurar y para el entrenador)."""
    by_frame: dict[int, list] = {}
    for tr in tracks:
        for ob in tr.observations:
            by_frame.setdefault(ob.frame, []).append((tr.track_id, ob))
    cap = cv2.VideoCapture(str(video_path))
    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    writer = cv2.VideoWriter(str(out_path), cv2.VideoWriter_fourcc(*"mp4v"), out_fps, (w, h))
    colors = [(0, 204, 255), (77, 77, 255), (136, 255, 77), (255, 128, 213), (255, 255, 255), (255, 229, 0)]
    scale = max(8, int(h * 0.35 / 20))  # píxeles por metro del minimapa
    cap.set(cv2.CAP_PROP_POS_FRAMES, first)
    idx = first
    from .court import COURT_LINES

    while idx < last:
        if (idx - first) % step != 0:
            if not cap.grab():
                break
            idx += 1
            continue
        ok, frame = cap.read()
        if not ok:
            break
        mini = np.full((20 * scale + 10, 10 * scale + 10, 3), (181, 109, 47), np.uint8)
        for a, b in COURT_LINES:
            pa = (int(a[0] * scale) + 5, int((20 - a[1]) * scale) + 5)
            pb = (int(b[0] * scale) + 5, int((20 - b[1]) * scale) + 5)
            cv2.line(mini, pa, pb, (255, 255, 255), 1)
        for pid, ob in by_frame.get(idx, []):
            k = int(pid[1:]) - 1
            col = colors[k % len(colors)]
            x1, y1, x2, y2 = map(int, ob.bbox)
            cv2.rectangle(frame, (x1, y1), (x2, y2), col, 2)
            cv2.putText(frame, pid, (x1, y1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.7, col, 2)
            cx, cy = ob.court_xy
            cv2.circle(mini, (int(cx * scale) + 5, int((20 - cy) * scale) + 5), 4, col, -1)
        mh, mw = mini.shape[:2]
        if mh < h and mw < w:
            frame[10 : 10 + mh, w - mw - 10 : w - 10] = mini
        writer.write(frame)
        idx += 1
    cap.release()
    writer.release()

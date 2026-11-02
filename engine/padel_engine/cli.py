"""Línea de comandos: ``padel-engine analizar | calibrar | sintetico | informe``."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv


def _cmd_analizar(a: argparse.Namespace) -> int:
    from .pipeline import PipelineConfig, run_pipeline

    names = json.loads(Path(a.nombres).read_text(encoding="utf-8")) if a.nombres else {}
    cfg = PipelineConfig(
        detector=a.detector,
        weights=a.pesos,
        detections_path=a.detecciones,
        device=a.dispositivo,
        imgsz=a.imgsz,
        analysis_fps=a.fps,
        max_players=a.jugadores,
        start_s=a.desde,
        end_s=a.hasta,
        annotated_video=a.video_anotado,
        stabilize=not a.sin_estabilizar,
        use_llm=not a.sin_ia,
        context={"tipo_sesion": a.tipo_sesion, "nivel": a.nivel},
        player_names=names,
    )
    res = run_pipeline(a.video, a.calibracion, a.salida, cfg)
    print(f"\nListo. Resultados en: {a.salida}")
    v = res["video"]
    print(f"  Fotogramas analizados: {v['fotogramas_validos']} de {v['fotogramas_procesados']} (descartados por cambio de plano: {v['fotogramas_descartados_cambio_plano']})")
    print(f"  Jugadores detectados: {', '.join(p['id'] for p in res['jugadores']) or 'ninguno'}")
    print(f"  Error de calibración: {res['calibracion']['error_reproyeccion_px']} px (revisa calibracion_check.png)")
    print(f"  Informe: {'IA' if res['informe']['generado_con_ia'] else 'plantilla (sin IA)'} -> informe.md")
    print(f"  Tiempo total: {res['tiempos']['total_s']} s")
    return 0


def _cmd_calibrar(a: argparse.Namespace) -> int:
    from .calibration import export_calibration_frame, interactive_calibration

    if a.solo_png:
        png = export_calibration_frame(a.video, Path(a.salida).with_suffix(".png"), a.fotograma)
        print(f"Fotograma con rejilla guardado en {png}.")
        print("Mira las coordenadas de al menos 4 puntos de la pista y escríbelas en un JSON como engine/examples/calibracion_ejemplo.json")
        return 0
    interactive_calibration(a.video, a.salida, a.fotograma)
    print(f"Calibración guardada en {a.salida}")
    return 0


def _cmd_sintetico(a: argparse.Namespace) -> int:
    from .synthetic import generate

    files = generate(a.salida, duration_s=a.duracion)
    print("Generado:")
    for k, v in files.items():
        print(f"  {k}: {v}")
    print(
        f"\nPrueba ahora:\n  padel-engine analizar {files['video']} --calibracion {files['calibracion']} "
        f"--detector replay --detecciones {files['detecciones']} --salida {Path(a.salida) / 'resultado'}"
    )
    return 0


def _cmd_informe(a: argparse.Namespace) -> int:
    """Regenera solo el informe a partir de un analisis.json (no usa GPU)."""
    from .report import build_report

    analysis = json.loads(Path(a.analisis).read_text(encoding="utf-8"))
    names = json.loads(Path(a.nombres).read_text(encoding="utf-8")) if a.nombres else {}
    md, meta = build_report(analysis, use_llm=not a.sin_ia, context={"tipo_sesion": a.tipo_sesion, "nivel": a.nivel}, names=names)
    out = Path(a.salida or Path(a.analisis).with_name("informe.md"))
    out.write_text(md, encoding="utf-8")
    print(f"Informe ({'IA' if meta['generado_con_ia'] else 'plantilla'}) guardado en {out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(prog="padel-engine", description="Motor de análisis de vídeo de pádel")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("analizar", help="Analiza un vídeo")
    p.add_argument("video")
    p.add_argument("--calibracion", required=True, help="JSON con los puntos de la pista")
    p.add_argument("--salida", required=True, help="Carpeta de resultados")
    p.add_argument("--detector", default="yolox", choices=["yolox", "ultralytics", "torchvision", "replay"])
    p.add_argument("--pesos", default=None, help="Modelo: yolox_s.onnx / yolox_m.onnx (defecto) / yolox_l.onnx, o pesos YOLO de ultralytics")
    p.add_argument("--detecciones", help="detecciones.json para --detector replay")
    p.add_argument("--dispositivo", default=None, help="cpu, cuda, mps... (auto por defecto)")
    p.add_argument("--imgsz", type=int, default=1280)
    p.add_argument("--fps", type=float, default=10.0, help="Fotogramas por segundo a analizar")
    p.add_argument("--jugadores", type=int, default=4, help="Número máximo de jugadores en pista")
    p.add_argument("--desde", type=float, default=0.0, help="Segundo inicial")
    p.add_argument("--hasta", type=float, default=None, help="Segundo final")
    p.add_argument("--nombres", help='JSON {"J1": "Lucía", ...} (no se envía a la IA)')
    p.add_argument("--tipo-sesion", default="partido", choices=["partido", "entrenamiento"])
    p.add_argument("--nivel", default="desconocido")
    p.add_argument("--sin-ia", action="store_true", help="Informe de plantilla, sin llamar al modelo de lenguaje")
    p.add_argument("--video-anotado", action="store_true", help="Genera video_anotado.mp4 de control")
    p.add_argument("--sin-estabilizar", action="store_true", help="Cámara totalmente fija: no corregir movimiento ni detectar cambios de plano")
    p.set_defaults(func=_cmd_analizar)

    c = sub.add_parser("calibrar", help="Marca los puntos de la pista en un fotograma")
    c.add_argument("video")
    c.add_argument("--salida", default="calibracion.json")
    c.add_argument("--fotograma", type=int, default=0)
    c.add_argument("--solo-png", action="store_true", help="Solo exporta un PNG con rejilla (sin ventana)")
    c.set_defaults(func=_cmd_calibrar)

    s = sub.add_parser("sintetico", help="Genera un vídeo sintético de prueba")
    s.add_argument("--salida", default="datos/sintetico")
    s.add_argument("--duracion", type=float, default=40.0)
    s.set_defaults(func=_cmd_sintetico)

    r = sub.add_parser("informe", help="Regenera el informe desde analisis.json")
    r.add_argument("analisis")
    r.add_argument("--salida")
    r.add_argument("--nombres")
    r.add_argument("--tipo-sesion", default="partido", choices=["partido", "entrenamiento"])
    r.add_argument("--nivel", default="desconocido")
    r.add_argument("--sin-ia", action="store_true")
    r.set_defaults(func=_cmd_informe)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

"""Prueba de punta a punta con el vídeo sintético (verdad conocida), sin GPU ni IA."""

import json

import numpy as np
import pytest

from padel_engine.pipeline import PipelineConfig, run_pipeline
from padel_engine.synthetic import generate


@pytest.fixture(scope="module")
def result(tmp_path_factory):
    d = tmp_path_factory.mktemp("synt")
    files = generate(d, duration_s=150.0)
    cfg = PipelineConfig(detector="replay", detections_path=str(files["detecciones"]), use_llm=False, annotated_video=True)
    analysis = run_pipeline(files["video"], files["calibracion"], d / "out", cfg)
    truth = json.loads(files["verdad"].read_text())
    return analysis, truth, d / "out"


def test_outputs_exist(result):
    analysis, _, out = result
    for name in ["analisis.json", "informe.md", "trayectorias.json", "recorridos.png", "calibracion_check.png", "video_anotado.mp4", "mapa_calor_J1.png"]:
        assert (out / name).exists(), name
    assert analysis["informe"]["generado_con_ia"] is False


def test_four_players_named_by_position(result):
    analysis, _, _ = result
    players = analysis["jugadores"]
    assert [p["id"] for p in players] == ["J1", "J2", "J3", "J4"]
    assert [p["campo"] for p in players] == ["cerca", "cerca", "lejos", "lejos"]
    assert [p["lado_habitual"] for p in players] == ["izquierda", "derecha", "izquierda", "derecha"]
    assert all(p["cobertura_pct"] > 90 for p in players)


def test_distance_close_to_truth(result):
    analysis, truth, _ = result
    fps = truth["fps"]
    n = int(150.0 * fps)
    # Orden de la verdad que corresponde a J1..J4 (cerca-izq, cerca-der, lejos-izq, lejos-der)
    for pid, key in zip(["J1", "J2", "J3", "J4"], ["A", "B", "C", "D"]):
        xy = np.array(truth["trayectorias"][key])[:n:3]  # mismo muestreo (10 fps)
        true_dist = np.linalg.norm(np.diff(xy, axis=0), axis=1).sum()
        est = next(p for p in analysis["jugadores"] if p["id"] == pid)["distancia_m"]
        assert abs(est - true_dist) / true_dist < 0.25, (pid, est, true_dist)


def test_zones_and_pairs(result):
    analysis, _, _ = result
    by_id = {p["id"]: p for p in analysis["jugadores"]}
    assert by_id["J3"]["zonas_pct"]["red"] > 60  # C juega en la red
    assert by_id["J4"]["zonas_pct"]["fondo"] > 60  # D juega al fondo
    far_pair = next(p for p in analysis["parejas"] if p["campo"] == "lejos")
    assert far_pair["desalineados_pct"] > 50
    texts = " ".join(o["texto"] for o in far_pair["observaciones"])
    assert "desalineada" in texts


def test_report_template_mentions_players(result):
    _, _, out = result
    md = (out / "informe.md").read_text(encoding="utf-8")
    assert "## J1" in md and "Tiempo por zona" in md

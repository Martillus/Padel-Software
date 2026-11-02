from padel_engine.report import apply_player_names, build_llm_payload
from padel_engine.tracking import PlayerObservation, SlotTracker


def _obs(f, x, y):
    return PlayerObservation(frame=f, t=f / 10, court_xy=(x, y), bbox=(0, 0, 1, 1), conf=0.9)


def test_tracker_keeps_identity_and_reacquires():
    tr = SlotTracker(max_players=2)
    for f in range(20):
        tr.update(f / 10, [_obs(f, 2 + 0.05 * f, 5), _obs(f, 8, 15)])
    # J del fondo desaparece 1 s y reaparece cerca de donde estaba
    for f in range(20, 30):
        tr.update(f / 10, [_obs(f, 3.0, 5)])
    for f in range(30, 40):
        tr.update(f / 10, [_obs(f, 3.0, 5), _obs(f, 7.8, 15.2)])
    tracks = tr.finalize()
    assert len(tracks) == 2
    near, far = tracks
    assert near.track_id == "J1" and far.track_id == "J2"
    assert len(near.observations) == 40 and len(far.observations) == 30
    assert all(o.court_xy[1] > 10 for o in far.observations)


def test_names_never_go_to_llm_and_are_applied_locally():
    analysis = {
        "video": {"duracion_analizada_s": 60},
        "jugadores": [{"id": "J1", "zonas_pct": {}, "_heatmap": [1], "observaciones": []}],
        "parejas": [],
    }
    payload = build_llm_payload(analysis, {"tipo_sesion": "entrenamiento"})
    assert "_heatmap" not in payload["jugadores"][0]
    assert "Lucía" not in str(payload)
    assert apply_player_names("J1 sube bien. J12 no.", {"J1": "Lucía"}) == "Lucía sube bien. J12 no."

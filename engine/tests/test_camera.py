import cv2
import numpy as np

from padel_engine.camera import CameraMotion


def _scene(rng):
    """Imagen con textura (como gradas/publicidad) y una 'pista' con líneas."""
    img = cv2.GaussianBlur(rng.integers(0, 255, (720, 1280, 3), dtype=np.uint8), (5, 5), 0)
    court = np.array([[300, 650], [980, 650], [800, 200], [480, 200]], np.int32)
    cv2.fillPoly(img, [court], (170, 100, 40))
    for y in (300, 420, 560):
        cv2.line(img, (200, y), (1080, y), (255, 255, 255), 3)
    cv2.line(img, (640, 200), (640, 650), (255, 255, 255), 3)
    return img, court


def test_recovers_camera_shift_and_rejects_other_shot():
    rng = np.random.default_rng(0)
    ref, court = _scene(rng)
    cam = CameraMotion(ref, court_polygon=court)

    # El móvil se mueve un poco: desplazamiento + ligero zoom
    M = np.array([[1.05, 0.0, -30.0], [0.0, 1.05, 12.0]])
    moved = cv2.warpAffine(ref, M, (1280, 720))
    H = cam.frame_to_reference(moved)
    assert H is not None
    p_moved = np.array([[[640.0 * 1.05 - 30, 420 * 1.05 + 12]]])
    back = cv2.perspectiveTransform(p_moved, H)[0, 0]
    assert np.allclose(back, [640, 420], atol=3)

    # Primer plano: misma "esquina con marcador" pero el resto es otra imagen
    other = cv2.GaussianBlur(rng.integers(0, 255, (720, 1280, 3), dtype=np.uint8), (5, 5), 0)
    other[:120, :300] = ref[:120, :300]
    assert cam.frame_to_reference(other) is None

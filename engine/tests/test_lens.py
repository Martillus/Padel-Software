import numpy as np

from padel_engine.court import KEYPOINTS, CourtHomography
from padel_engine.lens import LensModel, fit_lens


def test_fit_lens_straightens_lines_and_homography_roundtrip():
    true = LensModel(f=1024, cx=512, cy=288, k1=-0.6, k2=0.2)
    # Cámara ideal (sin distorsión) mirando la pista
    ideal = CourtHomography.from_points(
        {"near_service_left": (60, 470), "near_service_right": (960, 470), "far_left": (330, 60), "far_right": (690, 60)}
    )

    def to_image(court_pts):
        return true.distort(ideal.court_to_image(np.asarray(court_pts, float)))

    # Puntos a lo largo de líneas rectas de la pista, vistos con la lente que curva
    lines = {
        "near_service": to_image([[x, 3.05] for x in np.linspace(0.5, 9.5, 15)]),
        "far_service": to_image([[x, 16.95] for x in np.linspace(0.5, 9.5, 15)]),
        "center": to_image([[5, y] for y in np.linspace(3.5, 16.5, 15)]),
        "net": to_image([[x, 10] for x in np.linspace(0.5, 9.5, 15)]),
    }
    lens, before, after = fit_lens(list(lines.values()), (1024, 576))
    assert before > 2.0
    assert after < 0.3

    names = ["near_service_left", "near_service_right", "far_service_left", "far_service_right", "net_left", "net_right"]
    pts = {n: tuple(to_image([KEYPOINTS[n]])[0]) for n in names}
    hom = CourtHomography.from_points(pts, lens=lens)
    assert hom.reprojection_error_px < 1.0
    probe = np.array([[2.0, 5.0], [7.5, 12.0], [5.0, 18.0]])
    np.testing.assert_allclose(hom.image_to_court_pts(to_image(probe)), probe, atol=0.1)

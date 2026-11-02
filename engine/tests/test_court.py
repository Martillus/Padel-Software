import numpy as np
import pytest

from padel_engine.court import KEYPOINTS, CalibrationError, CourtHomography, in_court, side_of, zone_of
from padel_engine.synthetic import CAMERA_POINTS


def test_homography_roundtrip():
    hom = CourtHomography.from_points(CAMERA_POINTS)
    assert hom.reprojection_error_px < 1e-6
    pts = np.array([[1.0, 2.0], [5.0, 10.0], [9.0, 18.0]])
    back = hom.image_to_court_pts(hom.court_to_image(pts))
    np.testing.assert_allclose(back, pts, atol=1e-6)


def test_homography_from_other_points_matches():
    ref = CourtHomography.from_points(CAMERA_POINTS)
    names = ["near_service_left", "near_service_right", "net_left", "net_right", "far_left", "far_right"]
    img = ref.court_to_image(np.array([KEYPOINTS[n] for n in names]))
    hom = CourtHomography.from_points(dict(zip(names, map(tuple, img))))
    np.testing.assert_allclose(hom.image_to_court_pts(img), [KEYPOINTS[n] for n in names], atol=1e-3)


def test_needs_four_points():
    with pytest.raises(CalibrationError):
        CourtHomography.from_points({"near_left": (0, 0), "near_right": (1, 0), "far_left": (0, 1)})


def test_zones_and_sides():
    assert zone_of(9.0) == "red"
    assert zone_of(5.0) == "transicion"
    assert zone_of(1.0) == "fondo"
    assert zone_of(19.0) == "fondo"
    assert side_of(4) == "cerca" and side_of(15) == "lejos"
    assert list(in_court(np.array([[5, 5], [-2, 5], [10.5, 20.5]]), margin=1.0)) == [True, False, True]

"""Inspection axes use crowns rather than arbitrary cast bases."""
import base64
import hashlib
import struct

import pytest

np = pytest.importorskip("numpy")
from tools.build_week_eighteen_display_frames import crown_frame  # noqa: E402


def fixture(extra_base=False):
    triangles, labels = [], []
    for quadrant, sign in [(1, -1), (2, 1)]:
        for tooth in range(1, 8):
            x, y = sign * tooth * 2, tooth * tooth / 3
            triangles.append([[x, y, 0], [x + .1, y, 0], [x, y + .1, 0]])
            labels.append(quadrant * 10 + tooth)
    if extra_base:
        triangles.append([[-1000, 2000, 3000], [1000, 2000, 3000], [0, -2000, 3000]])
        labels.append(0)
    raw = bytes(80) + struct.pack("<I", len(triangles))
    for triangle in triangles:
        raw += struct.pack("<12fH", 0, 0, 1, *np.array(triangle).ravel(), 0)
    return raw, {"source_sha256": hashlib.sha256(raw).hexdigest(),
                 "labels_base64": base64.b64encode(bytes(labels)).decode()}


def test_cast_base_does_not_change_crown_frame():
    first = crown_frame(*fixture(), "upper")
    second = crown_frame(*fixture(extra_base=True), "upper")
    for key in ["up", "front", "origin", "crown_width_scan_units", "crown_depth_scan_units"]:
        assert np.allclose(first[key], second[key])
    up, front = np.array(first["up"]), np.array(first["front"])
    rotation = np.array([np.cross(up, front), up, front])
    assert np.allclose(rotation @ rotation.T, np.eye(3))
    assert np.isclose(np.linalg.det(rotation), 1)
    assert first["reviewed"] is False
    assert first["units"] == "unverified"


def test_rejects_wrong_source_and_incomplete_regions():
    raw, annotation = fixture()
    with pytest.raises(ValueError, match="binding"):
        crown_frame(raw, {**annotation, "source_sha256": "other"}, "upper")
    with pytest.raises(ValueError, match="Insufficient"):
        crown_frame(raw, {**annotation, "labels_base64": base64.b64encode(bytes(14)).decode()}, "upper")

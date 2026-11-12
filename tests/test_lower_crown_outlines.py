"""Lower-only geometry and annotation checks; no upper fixture is opened."""
import base64
import hashlib
import json
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")
from scipy.sparse.csgraph import connected_components  # noqa: E402
from orthoplan.segmentation.crown_outlines import separate_crowns  # noqa: E402

CASE = Path(__file__).resolve().parents[1] / "datasets/spec-07b7031938c84b1a9c98517b8bc4cdd3"
ORDER = [47, 46, 45, 44, 43, 42, 41, 31, 32, 33, 34, 35, 36, 37]


def test_lower_draft_count_connectivity_order_and_geometry_hash():
    folder = CASE / "annotations"
    recipe = json.loads((folder / "initial-lower-valley-recipe.json").read_text())
    report = json.loads((folder / "initial-lower-segmentation-report.json").read_text())
    before = json.loads((folder / "initial-lower-before-correction.json").read_text())
    after = json.loads((folder / "initial-lower-tooth-corrections.json").read_text())
    raw = (CASE / "initial-lower.stl").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == recipe["source_sha256"] == after["source_sha256"]
    dtype = np.dtype([("n", "<f4", (3,)), ("v", "<f4", (3, 3)), ("a", "<u2")])
    mesh = np.frombuffer(raw, dtype=dtype, offset=84)["v"].astype(float)
    prior = np.frombuffer(base64.b64decode(before["labels_base64"]), dtype="u1")
    expected = np.frombuffer(base64.b64decode(after["labels_base64"]), dtype="u1")
    labels, graph, _ = separate_crowns(mesh, prior, recipe["crowns"])
    assert np.array_equal(labels, expected)
    assert set(labels) == {0, *ORDER}
    assert np.all(labels[prior == 0] == 0)
    angles = []
    for tooth, row in zip(ORDER, report["teeth"]):
        faces = np.flatnonzero(labels == tooth)
        assert connected_components(graph[faces][:, faces], return_labels=False) == 1
        assert row["fdi"] == tooth and row["face_count"] == len(faces)
        assert np.isfinite(row["estimated_width_mm"]) and row["estimated_width_mm"] > 0
        assert row["flags"]  # No perfect anatomical-boundary claim.
        center = mesh[faces].mean(axis=(0, 1))
        assert (center[0] < 0) == (tooth // 10 == 4)
        angles.append(np.arctan2(center[0], -center[1] - 5))
    assert np.all(np.diff(angles) > 0)
    edges = graph.tocoo()
    cross = (labels[edges.row] != labels[edges.col]) & (labels[edges.row] != 0) & (labels[edges.col] != 0)
    assert not cross.any()
    assert after["reviewed"] is False and after["arch"] == "lower"


def test_touching_masks_get_a_context_buffer_and_fragments_are_removed():
    triangles = []
    for x in range(4):
        for y in range(3):
            a, b, c, d = [x, y, 0], [x + 1, y, 0], [x + 1, y + 1, 0], [x, y + 1, 0]
            triangles.extend([[a, b, c], [a, c, d]])
    # A small, disconnected floating triangle inside the first crown outline.
    triangles.append([[.2, .2, 1], [.3, .2, 1], [.2, .3, 1]])
    crowns = [{"fdi": 41, "outline_xy": [[-.1, -.1], [2.2, -.1], [2.2, 3.1], [-.1, 3.1]]},
              {"fdi": 31, "outline_xy": [[1.8, -.1], [4.1, -.1], [4.1, 3.1], [1.8, 3.1]]}]
    labels, graph, audit = separate_crowns(np.asarray(triangles), np.ones(len(triangles)), crowns)
    assert labels[-1] == 0
    assert audit["contact_buffer_faces_left_unlabeled"] > 0
    for tooth in [41, 31]:
        faces = np.flatnonzero(labels == tooth)
        assert len(faces) and connected_components(graph[faces][:, faces], return_labels=False) == 1

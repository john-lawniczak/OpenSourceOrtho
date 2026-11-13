"""Private automatic draft artifacts stay source-bound and never overwrite painting."""
import base64
import fnmatch
import json

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("scipy")

from orthoplan.datasets import SAMPLE_CASE_DIR, resolve_published_asset  # noqa: E402
from orthoplan.region_corrections import baseline_source, load_baseline_corrections, validate_corrections  # noqa: E402
from tools.seed_week_eighteen_labels import CAPTURES, OUTPUT, install  # noqa: E402
from tools.week_eighteen_seed_geometry import fit_crowns, project_crowns  # noqa: E402


@pytest.mark.parametrize("arch", ["upper", "lower"])
def test_prepared_drafts_are_private_unreviewed_and_preserve_existing_saves(arch, tmp_path, monkeypatch):
    if not OUTPUT.exists():
        pytest.skip("Private development painting drafts are absent from public releases")
    monkeypatch.setenv("ORTHOPLAN_REGION_CORRECTIONS", str(tmp_path))
    correction = json.loads((OUTPUT / f"{arch}-corrections.json").read_text())
    report = json.loads((OUTPUT / f"{arch}-report.json").read_text())
    summary = validate_corrections(correction, arch, baseline_source(arch, "progress-02", CAPTURES[arch]))
    assert len(summary["tooth_ids"]) == 14
    assert not correction["reviewed"] and correction["provenance"] == "automatic-draft"
    assert set(summary["tooth_ids"]).isdisjoint({18, 28, 38, 48})
    saved = install(arch, correction, report)
    assert saved["ok"] and saved["review_status"] == "draft"
    assert not install(arch, correction, report)["ok"]
    assert load_baseline_corrections(arch, visit="progress-02", capture=CAPTURES[arch])["path"] == saved["path"]
    assert load_baseline_corrections(arch, visit="progress-02")["saved"] is False
    asset = (OUTPUT / f"{arch}-corrections.json").relative_to(SAMPLE_CASE_DIR)
    reference = f"datasets/{SAMPLE_CASE_DIR.name}/{asset}"
    assert resolve_published_asset(reference) is None
    assert fnmatch.fnmatch(reference, "datasets/**/private/*")
    assert len(base64.b64decode(correction["labels_base64"])) == correction["face_count"]


def test_projection_keeps_unsupported_and_disconnected_faces_unlabeled():
    def square(x):
        a, b, c, d = [x, 0, 0], [x+1, 0, 0], [x+1, 1, 0], [x, 1, 0]
        return [[a, b, c], [a, c, d]]
    mesh = np.array(square(0) + square(10) + square(30), dtype=float)
    labels = np.array([11, 11, 21, 21, 11, 11], dtype=np.uint8)
    projected, _ = project_crowns(mesh, mesh, labels, np.eye(4), absent=[21])
    assert projected.tolist() == [11, 11, 0, 0, 0, 0]
    distant, _ = project_crowns(mesh, mesh + [0, 0, 10], labels, np.eye(4))
    assert not distant.any()


def test_multistart_registration_recovers_a_proper_rotation_without_scale():
    rng = np.random.default_rng(901)
    source = rng.normal(size=(40, 3, 3)) * [12, 7, 3]
    rotation = np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1]])
    target = source @ rotation.T + [16, -8, 25]
    matrix, report = fit_crowns(source, target, np.full(40, 11, dtype=np.uint8))
    np.testing.assert_allclose(matrix[:3, :3], rotation, atol=1e-6)
    np.testing.assert_allclose(matrix[:3, 3], [16, -8, 25], atol=1e-6)
    assert report["source_crown_p80_residual"] < 1e-6

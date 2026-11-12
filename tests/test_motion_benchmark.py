import base64
import copy
import pytest

pytest.importorskip("numpy")
pytest.importorskip("scipy")
from orthoplan.longitudinal.benchmark import score_motion  # noqa: E402


def example():
    tooth = dict(
        tooth="11",
        target_tooth="11",
        pivot=[0, 0, 0],
        translation=[0, 0, 0],
        quaternion_xyzw=[0, 0, 0, 1],
        status="estimated-draft",
        face_label=1,
        target_faces=[0, 1],
    )
    p = dict(
        frame="test",
        sources=[dict(sha256="a"), dict(sha256="b")],
        teeth=[tooth],
        moving_face_labels_base64=base64.b64encode(bytes([1, 1])).decode(),
    )
    t = dict(
        schema="ortho-motion-truth-v1",
        frame="test",
        source_hashes=["a", "b"],
        kind="synthetic",
        teeth=[copy.deepcopy(tooth)],
        source_face_tooth_ids=[11, 11],
        target_face_tooth_ids=[11, 11],
        no_motion=True,
        units="source",
        translation_tolerance=0.1,
        rotation_tolerance_deg=1,
    )
    return p, t


def test_known_zero_motion_and_deliberate_errors():
    p, t = example()
    assert score_motion(p, t)["translation_rmse"] == 0
    p["teeth"][0]["translation"] = [0.5, 0, 0]
    t["target_face_tooth_ids"] = [12, 12]
    r = score_motion(p, t)
    assert r["translation_rmse"] == 0.5
    assert r["false_motion_regions"] == 1
    assert r["identity_errors"] == 1


def test_unreviewed_real_and_wrong_hash_fail_and_missing_is_not_perfect():
    p, t = example()
    t["kind"] = "reviewed-real"
    with pytest.raises(ValueError, match="review"):
        score_motion(p, t)
    t["kind"] = "synthetic"
    t["source_hashes"] = ["bad"]
    with pytest.raises(ValueError, match="bound"):
        score_motion(p, t)
    t["source_hashes"] = ["a", "b"]
    p["teeth"][0]["status"] = "held-unmatched"
    r = score_motion(p, t)
    assert r["missing_regions"] == 1 and r["translation_rmse"] is None


def test_review_flags_and_boundary_errors_are_not_hidden_by_crown_accuracy():
    p, t = example()
    t.update(
        kind="reviewed-real",
        review=dict(reviewer="Reviewer", boundaries="true", correspondence=True, poses=True),
    )
    with pytest.raises(ValueError, match="review"):
        score_motion(p, t)
    t.update(kind="synthetic", source_face_tooth_ids=[11, 0])
    report = score_motion(p, t)
    assert report["source_boundary_accuracy"] == 1
    assert report["boundary_regions"][0]["iou"] == 0.5
    assert report["boundary_regions"][0]["precision"] == 0.5
    assert report["boundary_regions"][0]["false_positive_faces"] == 1
    p["teeth"][0]["status"] = "held-unmatched"
    report = score_motion(p, t)
    assert report["fit_coverage"] == 0 and report["translation_rmse"] is None

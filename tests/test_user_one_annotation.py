"""Published upper corrections preserve painted faces and use the reported inventory."""
import base64
import hashlib
import json

import pytest

from orthoplan.datasets import SAMPLE_CASE_DIR, resolve_published_asset, SAMPLE_SPECIMEN_ID
from orthoplan.region_corrections import baseline_source, validate_corrections


def test_upper_posterior_draft_is_reproducible_and_preserves_user_paint():
    np = pytest.importorskip("numpy")
    from tools.correct_user_one_upper_labels import correct_labels, restoration_masks

    folder = SAMPLE_CASE_DIR / "annotations"
    before = json.loads((folder / "initial-upper-before-posterior-correction.json").read_text())
    after = json.loads((folder / "initial-upper-tooth-corrections.json").read_text())
    recipe = json.loads((folder / "initial-upper-posterior-recipe.json").read_text())
    raw = (SAMPLE_CASE_DIR / "initial-upper.stl").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == before["source_sha256"] == after["source_sha256"]
    dtype = np.dtype([("n", "<f4", (3,)), ("v", "<f4", (3, 3)), ("a", "<u2")])
    triangles = np.frombuffer(raw, dtype=dtype, offset=84)["v"].astype(float)
    previous = np.frombuffer(base64.b64decode(before["labels_base64"]), dtype="u1")
    updated = np.frombuffer(base64.b64decode(after["labels_base64"]), dtype="u1")
    masks = restoration_masks(SAMPLE_CASE_DIR, recipe)
    assert np.array_equal(correct_labels(triangles, previous, recipe, masks), updated)
    assert np.array_equal(updated[np.isin(previous, [21, 22])], previous[np.isin(previous, [21, 22])])
    assert np.all(updated[previous == 13] == 23)
    assert np.all(np.isin(updated[previous == 0], [0, 11, 12]))
    prior_front = json.loads((folder / "initial-upper-before-front-restoration.json").read_text())
    prior_labels = np.frombuffer(base64.b64decode(prior_front["labels_base64"]), dtype="u1")
    assert np.array_equal(updated[prior_labels != 0], prior_labels[prior_labels != 0])
    assert np.count_nonzero(updated == 11) == 18019
    assert np.count_nonzero(updated == 12) == 8322
    assert np.all(masks[(prior_labels == 0) & (updated == 11)] == 8)
    assert np.all(masks[(prior_labels == 0) & (updated == 12)] == 9)
    assert {15, 16, 17, 25, 26, 27}.issubset(set(updated))
    assert not {18, 28}.intersection(updated)
    assert not after["reviewed"]
    validate_corrections(after, "upper", baseline_source("upper"))
    for name in ["initial-upper-tooth-corrections.json", "initial-upper-posterior-recipe.json"]:
        assert resolve_published_asset(f"/datasets/{SAMPLE_SPECIMEN_ID}/annotations/{name}")


def test_reported_wisdom_removal_has_no_invented_extraction_date():
    context = json.loads((SAMPLE_CASE_DIR / "treatment-context.json").read_text())
    dentition = context["dentition"]
    assert dentition["absent_fdi"] == ["18", "28", "38", "48"]
    assert dentition["extraction_dates"] is None
    assert "Contributor" in dentition["provenance"]

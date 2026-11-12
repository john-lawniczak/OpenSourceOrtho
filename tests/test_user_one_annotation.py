"""Published upper corrections preserve painted faces and use the reported inventory."""
import base64
import hashlib
import json

import numpy as np

from orthoplan.datasets import SAMPLE_CASE_DIR, resolve_published_asset, SAMPLE_SPECIMEN_ID
from orthoplan.region_corrections import baseline_source, validate_corrections
from tools.correct_user_one_upper_labels import correct_labels


def test_upper_posterior_draft_is_reproducible_and_preserves_user_paint():
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
    assert np.array_equal(correct_labels(triangles, previous, recipe), updated)
    assert np.array_equal(updated[np.isin(previous, [21, 22])], previous[np.isin(previous, [21, 22])])
    assert np.all(updated[previous == 13] == 23)
    assert np.all(updated[previous == 0] == 0)
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

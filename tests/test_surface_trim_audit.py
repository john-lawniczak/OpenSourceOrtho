"""The saved cleanup is an exact private draft, with removals explicitly audited."""
import base64
import hashlib
import json

import pytest

from orthoplan.datasets import SAMPLE_CASE_DIR, resolve_published_asset

pytest.importorskip("numpy", reason="Surface trim auditing requires the motion-preview extra")
from tools.audit_surface_trim import audit_trim  # noqa: E402

ARCHIVE = SAMPLE_CASE_DIR / "private/surface-edits/week-18-lower-cleaned"


@pytest.fixture
def archived():
    if not ARCHIVE.exists():
        pytest.skip("Private saved cleanup is absent from public releases")
    bundle = json.loads((ARCHIVE / "repair-bundle.json").read_text())
    source = (SAMPLE_CASE_DIR / bundle["scan"]["repair"]["sourceFilename"]).read_bytes()
    labels = json.loads((SAMPLE_CASE_DIR / "private/painting-seeds/week-18/lower-corrections.json").read_text())
    return bundle, source, labels


def test_saved_cleanup_is_exact_and_caveat_is_retained(archived):
    report = audit_trim(*archived)
    assert report == json.loads((ARCHIVE / "audit.json").read_text())
    assert report["removed_faces"] == 66640
    assert report["removed_by_prior_label"]["43"] == 28
    assert report["label_changes_on_retained_faces"] == 0
    assert len(report["all_present_labels_retained"]) == 14
    assert not archived[0]["labels"]["reviewed"]
    for file in ARCHIVE.iterdir():
        reference = "datasets/" + str(file.relative_to(SAMPLE_CASE_DIR.parent))
        assert resolve_published_asset(reference) is None


def test_audit_rejects_changed_geometry_even_with_updated_hash(archived):
    bundle, source, labels = archived
    data = bytearray(base64.b64decode(bundle["stlBase64"]))
    data[96] ^= 1
    bundle["stlBase64"] = base64.b64encode(data).decode()
    bundle["scan"]["sha256"] = hashlib.sha256(data).hexdigest()
    with pytest.raises(ValueError, match="ordered exact subset"):
        audit_trim(bundle, source, labels)

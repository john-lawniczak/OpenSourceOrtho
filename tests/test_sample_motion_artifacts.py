"""The bundled motion estimates remain source-bound, draft, and private-scan-free."""

import base64
import hashlib
import json
import math
import struct

from orthoplan.datasets import SAMPLE_CASE_DIR, resolve_published_asset
from orthoplan.evaluation.finding import Finding, FindingProvenance, lint_finding


def test_motion_preview_sources_masks_and_advisories():
    for arch in ["upper", "lower"]:
        path = SAMPLE_CASE_DIR / f"derived/progress-01-motion-{arch}.json"
        preview = json.loads(path.read_text())
        assert resolve_published_asset(f"/datasets/{SAMPLE_CASE_DIR.name}/derived/{path.name}") == path
        assert preview["status"] == "estimated-unreviewed"
        assert preview["units"] == "source-coordinate-units-unverified"
        assert preview["weeks"] == [1, 7]
        assert [s["filename"] for s in preview["sources"]] == [
            f"initial-{arch}.stl", f"progress-01-{arch}.stl"]
        for source in preview["sources"]:
            raw = (SAMPLE_CASE_DIR / source["filename"]).read_bytes()
            assert hashlib.sha256(raw).hexdigest() == source["sha256"]
        baseline = (SAMPLE_CASE_DIR / preview["sources"][0]["filename"]).read_bytes()
        labels = base64.b64decode(preview["moving_face_labels_base64"], validate=True)
        assert len(labels) == struct.unpack_from("<I", baseline, 80)[0]
        assert set(labels) == {0, *(t["face_label"] for t in preview["teeth"])}
        assert sum(t["status"].startswith("estimated") for t in preview["teeth"]) >= 10
        for tooth in preview["teeth"]:
            assert tooth["reviewed"] is False
            assert math.isclose(math.hypot(*tooth["quaternion_xyzw"]), 1, abs_tol=1e-8)
            assert all(math.isfinite(v) for v in tooth["translation"])
            if tooth["status"] == "held-unmatched":
                assert tooth["translation"] == [0, 0, 0]
            if (tooth.get("assignment_evidence") or {}).get("ambiguous"):
                assert tooth["status"] in {"estimated-weak", "held-unmatched"}
        for finding in preview["advisory_findings"]:
            assert lint_finding(Finding.model_validate(finding)).provenance == FindingProvenance.MODEL

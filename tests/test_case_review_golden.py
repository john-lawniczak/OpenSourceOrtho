from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from orthoplan.case_review import build_case_review_export, case_review_digest_payload
from orthoplan.hashing import canonical_json, sha256_text
from orthoplan.model.assets import MeshAsset, MeshUnits, UploadedScan
from orthoplan.model.plan import Stage, ToothDelta, ToothId, TreatmentPlan

FIXTURE = Path(__file__).resolve().parents[1] / "mobile" / "fixtures" / "case-review-v1.json"


def _golden_plan() -> TreatmentPlan:
    return TreatmentPlan(
        id="golden-case-001",
        title="Golden mobile handoff case",
        scans=[
            UploadedScan(
                asset=MeshAsset(
                    id="scan-upper",
                    format="stl",
                    units=MeshUnits.MM,
                    vertex_count=12,
                    face_count=20,
                    created_at=datetime(2026, 1, 1, tzinfo=UTC),
                )
            )
        ],
        stages=[
            Stage(
                index=0,
                deltas=[ToothDelta(tooth=ToothId(value="11"), translate_x_mm=0.2)],
            )
        ],
    )


def test_case_review_v1_golden_fixture_matches_engine_output() -> None:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    generated = build_case_review_export(
        _golden_plan(),
        base_url="https://ortho.example/app",
        created_at=datetime(2026, 6, 11, 12, 0, tzinfo=UTC),
    )

    assert fixture == generated
    assert fixture["schema"] == "orthoplan-case-review-v1"
    assert fixture["kind"] == "stored-review"
    assert fixture["editable"]["in_mobile"] is False
    assert fixture["editable"]["requires_browser_engine"] is True
    assert fixture["handoff"]["qr_payload"] == fixture["handoff"]["open_url"]
    assert fixture["review_sha256"] == sha256_text(canonical_json(case_review_digest_payload(fixture)))

from __future__ import annotations

from datetime import UTC, datetime

from orthoplan.case_review import (
    CASE_REVIEW_SCHEMA,
    build_case_review_export,
    case_review_digest_payload,
    case_review_payload,
)
from orthoplan.hashing import canonical_json, sha256_text
from orthoplan.model.assets import CaseRecord, MeshAsset, MeshUnits, UploadedScan
from orthoplan.model.plan import Stage, ToothDelta, ToothId, TreatmentPlan

_EPOCH = datetime(2026, 1, 1, tzinfo=UTC)


def _plan(plan_id: str = "case-1", records=None) -> TreatmentPlan:
    return TreatmentPlan(
        id=plan_id,
        title="Handoff case",
        scans=[UploadedScan(asset=MeshAsset(
            id="scan", format="stl", units=MeshUnits.MM, vertex_count=1, face_count=1,
            created_at=_EPOCH))],
        case_records=records or [],
        stages=[Stage(index=0, deltas=[ToothDelta(tooth=ToothId(value="11"), translate_x_mm=0.2)])],
    )


def test_export_is_opaque_stored_review_with_tier_and_gaps() -> None:
    review = build_case_review_export(_plan())
    assert review["schema"] == CASE_REVIEW_SCHEMA
    assert review["kind"] == "stored-review"
    assert review["review_tier"]["tier"] == "stl-only"
    # Unresolved anatomy gaps are listed for a surface-only review.
    domains = {gap["domain"] for gap in review["unresolved_data_gaps"]}
    assert "roots" in domains and "cbct_anatomy" in domains
    assert review["findings_summary"]["total"] >= 0
    assert len(review["plan_sha256"]) == 64
    assert len(review["review_sha256"]) == 64


def test_export_marks_plan_as_browser_engine_only() -> None:
    review = build_case_review_export(_plan())
    assert review["editable"]["in_mobile"] is False
    assert review["editable"]["requires_browser_engine"] is True


def test_handoff_prefers_hosted_url_else_deep_link() -> None:
    hosted = build_case_review_export(_plan("case 2/upper"), base_url="https://host.example/app/")
    assert hosted["handoff"]["open_url"] == "https://host.example/app/?case=case+2%2Fupper"
    assert hosted["handoff"]["qr_payload"] == "https://host.example/app/?case=case+2%2Fupper"
    assert hosted["handoff"]["deep_link"] == "orthoplan://case/case%202%2Fupper"

    local = build_case_review_export(_plan("c3"))
    assert local["handoff"]["open_url"] is None
    assert local["handoff"]["qr_payload"] == "orthoplan://case/c3"


def test_handoff_rejects_non_web_base_urls() -> None:
    review = build_case_review_export(_plan("c4"), base_url="javascript:alert(1)")
    assert review["handoff"]["open_url"] is None
    assert review["handoff"]["qr_payload"] == "orthoplan://case/c4"


def test_review_hash_is_stable_for_same_plan() -> None:
    a = build_case_review_export(_plan(), created_at=_fixed())
    b = build_case_review_export(_plan(), created_at=_fixed())
    assert a["review_sha256"] == b["review_sha256"]
    assert a["review_sha256"] == sha256_text(canonical_json(case_review_digest_payload(a)))


def test_cbct_attached_review_reports_cbct_status() -> None:
    review = build_case_review_export(
        _plan(records=[CaseRecord(id="cb", kind="cbct", local_reference="records/cb.dcm")])
    )
    assert review["cbct_status"] == "attached"
    assert review["review_tier"]["tier"] == "cbct-attached"


def test_payload_wrapper_handles_ok_and_error() -> None:
    ok = case_review_payload({"plan": _plan().model_dump(mode="json")})
    assert ok["ok"] is True
    assert ok["review"]["schema"] == CASE_REVIEW_SCHEMA

    bad = case_review_payload({"plan": {"title": "no id"}})
    assert bad["ok"] is False
    assert bad["errors"]


def _fixed():
    from datetime import UTC, datetime

    return datetime(2026, 6, 11, 12, 0, tzinfo=UTC)

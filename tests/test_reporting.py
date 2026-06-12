from __future__ import annotations

from datetime import UTC, datetime

from orthoplan import __version__
from orthoplan.model import Stage, ToothDelta, ToothId, TreatmentPlan
from orthoplan.reporting import build_handoff_report, plan_digest, report_to_json


def _plan(delta: float = 0.2) -> TreatmentPlan:
    return TreatmentPlan(
        id="report-plan",
        title="Report plan",
        stages=[
            Stage(
                index=0,
                deltas=[ToothDelta(tooth=ToothId(value="11"), translate_x_mm=delta)],
            )
        ],
    )


def test_plan_digest_is_stable_and_changes_with_input() -> None:
    assert plan_digest(_plan()) == plan_digest(_plan())
    assert plan_digest(_plan()) != plan_digest(_plan(delta=0.3))


def test_handoff_report_binds_plan_engine_and_evaluation() -> None:
    report = build_handoff_report(
        _plan(),
        created_at=datetime(2026, 6, 4, 12, 0, tzinfo=UTC),
    )

    assert report["schema"] == "orthoplan-report-v1"
    assert report["engine"]["version"] == __version__
    assert len(report["plan"]["sha256"]) == 64
    assert len(report["evaluation_sha256"]) == 64
    assert len(report["report_sha256"]) == 64
    assert report["evaluation"]["ok"] is True
    assert report["evaluation"]["data_gap_actions"]
    assert report["evaluation"]["findings"]
    assert report["review"]["status"] == "generated"


def test_evaluation_digest_is_stable_for_same_plan_and_differs_for_changes() -> None:
    report_a = build_handoff_report(_plan())
    report_b = build_handoff_report(_plan())
    report_changed = build_handoff_report(_plan(delta=0.3))

    assert report_a["evaluation_sha256"] == report_b["evaluation_sha256"]
    assert report_a["evaluation_sha256"] != report_changed["evaluation_sha256"]


def test_report_json_is_sorted_for_reproducible_handoff() -> None:
    report = build_handoff_report(
        _plan(),
        created_at=datetime(2026, 6, 4, 12, 0, tzinfo=UTC),
    )
    first = report_to_json(report)
    second = report_to_json(report)
    assert first == second
    assert first.splitlines()[1].startswith('  "created_at"')


def test_report_labels_review_tier_and_lists_unresolved_surface_gaps() -> None:
    report = build_handoff_report(_plan())
    assert report["review_tier"]["tier"] == "stl-only"
    assert report["review_tier"]["root_bone_aware"] is False
    domains = {gap["domain"] for gap in report["unresolved_data_gaps"]}
    assert {"roots", "alveolar_bone", "periodontal_status", "occlusion", "cbct_anatomy"} <= domains


def test_report_can_include_reviewer_and_hmac_signature() -> None:
    report = build_handoff_report(
        _plan(),
        created_at=datetime(2026, 6, 4, 12, 0, tzinfo=UTC),
        reviewer="Dr. Example",
        signing_key="secret",
    )

    assert report["review"]["reviewer"] == "Dr. Example"
    assert report["signature"]["algorithm"] == "HMAC-SHA256"
    assert report["signature"]["scope"] == "report_sha256"
    assert len(report["signature"]["value"]) == 64

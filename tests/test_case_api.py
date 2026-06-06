from __future__ import annotations

from pathlib import Path

from orthoplan.case_api import (
    case_versions_payload,
    list_cases_payload,
    save_plan_version_payload,
)
from orthoplan.model.plan import Stage, ToothDelta, TreatmentPlan


def _plan(plan_id: str = "caseA", x: float = 0.2) -> dict:
    plan = TreatmentPlan(
        id=plan_id,
        title="My case",
        stages=[Stage(index=0, deltas=[ToothDelta(tooth={"system": "FDI", "value": "11"}, translate_x_mm=x)])],
    )
    return plan.model_dump(mode="json")


def test_save_appends_versions(tmp_path: Path) -> None:
    store = tmp_path / "cases.json"
    r1 = save_plan_version_payload({"plan": _plan(), "note": "first"}, store_path=store)
    r2 = save_plan_version_payload({"plan": _plan(x=0.3), "note": "second"}, store_path=store)
    assert r1["ok"] and r1["version"]["version_id"] == "v0001"
    assert r2["version"]["version_id"] == "v0002"
    assert len(r2["versions"]) == 2
    assert store.exists()


def test_versions_carry_distinct_hashes_and_snapshots(tmp_path: Path) -> None:
    store = tmp_path / "cases.json"
    save_plan_version_payload({"plan": _plan(x=0.2)}, store_path=store)
    save_plan_version_payload({"plan": _plan(x=0.3)}, store_path=store)
    result = case_versions_payload("caseA", store_path=store)
    assert result["ok"] is True
    hashes = {v["plan_hash"] for v in result["versions"]}
    assert len(hashes) == 2  # different plans -> different content hashes
    assert result["versions"][0]["snapshot"]["id"] == "caseA"


def test_list_cases(tmp_path: Path) -> None:
    store = tmp_path / "cases.json"
    save_plan_version_payload({"plan": _plan("caseA")}, store_path=store)
    save_plan_version_payload({"plan": _plan("caseB")}, store_path=store)
    cases = {c["case_id"]: c for c in list_cases_payload(store_path=store)["cases"]}
    assert set(cases) == {"caseA", "caseB"}
    assert cases["caseA"]["version_count"] == 1


def test_unknown_case_is_error_not_raise(tmp_path: Path) -> None:
    result = case_versions_payload("nope", store_path=tmp_path / "cases.json")
    assert result["ok"] is False


def test_invalid_plan_is_error_not_raise(tmp_path: Path) -> None:
    result = save_plan_version_payload({"plan": {"title": "no id"}}, store_path=tmp_path / "cases.json")
    assert result["ok"] is False
    assert result["errors"]


def test_custom_case_id_overrides_plan_id(tmp_path: Path) -> None:
    store = tmp_path / "cases.json"
    save_plan_version_payload({"plan": _plan("plan-x"), "case_id": "grouped"}, store_path=store)
    cases = list_cases_payload(store_path=store)["cases"]
    assert cases[0]["case_id"] == "grouped"

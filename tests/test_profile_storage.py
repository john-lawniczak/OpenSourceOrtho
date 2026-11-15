"""Profile IDs isolate local records without moving legacy/default data."""

from http.client import HTTPConnection
import json
from pathlib import Path
from uuid import uuid4

import pytest

from orthoplan.geometry_jobs import GeometryJobs
from orthoplan.profile_storage import current_profile, profile_case_store
from orthoplan.region_corrections import correction_store
from orthoplan.research_store import records, save_record
from test_server import server  # noqa: F401
from test_case_api import _plan
from test_region_corrections import record


def request(port, method, path, identity="default", payload=None):
    connection = HTTPConnection("127.0.0.1", port)
    try:
        connection.request(
            method,
            path,
            json.dumps(payload) if payload else None,
            {"X-Ortho-Profile": identity, "Content-Type": "application/json"},
        )
        response = connection.getresponse()
        return response.status, json.loads(response.read())
    finally:
        connection.close()


def test_http_profiles_isolate_same_case_id_and_painting_notes(server, tmp_path, monkeypatch):  # noqa: F811
    monkeypatch.setenv("ORTHOPLAN_CASE_STORE", str(tmp_path / "cases.json"))
    monkeypatch.setenv("ORTHOPLAN_REGION_CORRECTIONS", str(tmp_path / "labels"))
    child = str(uuid4())
    assert request(
        server, "POST", "/api/plan/version", payload={"plan": _plan(), "note": "parent"}
    )[1]["ok"]
    assert request(server, "GET", "/api/cases", child)[1]["cases"] == []
    assert request(
        server, "POST", "/api/plan/version", child, {"plan": _plan(x=0.4), "note": "child"}
    )[1]["ok"]
    parent_versions = request(server, "GET", "/api/cases/caseA")[1]["versions"]
    child_versions = request(server, "GET", "/api/cases/caseA", child)[1]["versions"]
    assert len(parent_versions) == len(child_versions) == 1
    assert parent_versions[0]["note"] == "parent" and child_versions[0]["note"] == "child"
    painting = {"arch": "lower", "corrections": record(), "notes": "Parent painting"}
    assert request(server, "POST", "/api/region-corrections", payload=painting)[1]["ok"]
    assert request(server, "GET", "/api/painting-notes", child)[1]["entries"] == []
    assert request(server, "GET", "/api/region-corrections/lower", child)[1]["saved"] is False
    assert (
        request(server, "GET", "/api/painting-notes")[1]["entries"][0]["notes"] == "Parent painting"
    )
    assert request(server, "GET", "/api/cases", "../../outside")[0] == 400
    assert (
        request(server, "POST", "/api/plan/version", "../../outside", {"plan": _plan()})[0] == 400
    )


def test_research_and_worker_capture_profile_context(tmp_path, monkeypatch):
    monkeypatch.setenv("ORTHOPLAN_RESEARCH_STORE", str(tmp_path / "research"))
    monkeypatch.setenv("ORTHOPLAN_REGION_CORRECTIONS", str(tmp_path / "labels"))
    assert correction_store() == tmp_path / "labels"
    save_record("reviews", {"note": "parent"})
    identity = str(uuid4())
    token = current_profile.set(identity)
    manager = GeometryJobs()
    try:
        assert correction_store() == tmp_path / "labels" / "profiles" / identity
        assert records("reviews") == []
        save_record("reviews", {"note": "child"})
        job = manager.start(
            "evaluate", {"id": "profile-job"}, workspace=tmp_path, ui_dir=Path("ui")
        )
        source = Path(manager.jobs[job["job_id"]]["directory"].name) / "request.json"
        assert json.loads(source.read_text())["profile_id"] == identity
        current_profile.reset(token)
        token = current_profile.set("default")
        assert manager.get(job["job_id"], cancel=True)["status"] == "missing"
        assert [r["note"] for r in records("reviews")] == ["parent"]
    finally:
        current_profile.reset(token)
        manager.close()


@pytest.mark.parametrize("identity", ["../parent", "DEFAULT", "", "123", "a" * 36])
def test_invalid_ids_cannot_select_paths(identity):
    with pytest.raises(ValueError):
        profile_case_store(Path("cases.json"), identity)

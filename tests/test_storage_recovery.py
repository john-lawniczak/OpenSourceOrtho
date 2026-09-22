"""Regression checks for interrupted writes and damaged case history."""
from __future__ import annotations

import json
from functools import partial
from pathlib import Path

import pytest

from orthoplan.case_api import (
    case_versions_payload, list_cases_payload, save_plan_version_payload,
)
from orthoplan.cases import CaseStore, read_case_store, write_case_store
from orthoplan.io import atomic
from orthoplan.mesh_workspace import MeshRegistry, read_registry, write_registry
from orthoplan.model.plan import TreatmentPlan


@pytest.mark.parametrize("failure", ["fsync", "replace"])
@pytest.mark.parametrize("kind", ["cases", "meshes"])
def test_interrupted_metadata_save_preserves_previous_document(tmp_path, monkeypatch, failure, kind):
    path = tmp_path / ("cases.json" if kind == "cases" else "mesh_registry.json")
    if kind == "cases":
        store = CaseStore()
        store.add_version("case", TreatmentPlan(id="plan", title="Original"))
        write_case_store(store, path)
        store.add_version("case", TreatmentPlan(id="plan", title="Updated"))
        save = partial(write_case_store, store, path)
    else:
        registry = MeshRegistry()
        write_registry(registry, tmp_path)
        save = partial(write_registry, registry, tmp_path)
    original = path.read_bytes()

    def fail(*args):
        raise OSError("simulated interrupted save")

    monkeypatch.setattr(atomic.os, failure, fail)
    with pytest.raises(OSError, match="interrupted"):
        save()
    assert path.read_bytes() == original
    assert list(tmp_path.iterdir()) == [path]
    if kind == "cases":
        assert len(read_case_store(path).cases["case"].versions) == 1
    else:
        assert read_registry(tmp_path).entries == {}


@pytest.mark.parametrize("damage", ["truncated", "invalid_utf8", "snapshot", "hash", "directory"])
def test_damaged_history_returns_errors_and_is_not_overwritten(tmp_path: Path, damage):
    path = tmp_path / "cases.json"
    payload = {"plan": TreatmentPlan(id="plan", title="Original").model_dump(mode="json")}
    assert save_plan_version_payload(payload, store_path=path)["ok"]
    if damage == "truncated":
        path.write_text('{"cases":')
    elif damage == "invalid_utf8":
        path.write_bytes(b"\xff")
    elif damage == "directory":
        path.unlink()
        path.mkdir()
    else:
        data = json.loads(path.read_text())
        version = data["cases"]["plan"]["versions"][0]
        if damage == "snapshot":
            version["snapshot"]["title"] = "Unrecorded edit"
        else:
            version["plan_hash"] = "0" * 64
        path.write_text(json.dumps(data))
    original = path.read_bytes() if path.is_file() else None
    for result in (
        list_cases_payload(store_path=path),
        case_versions_payload("plan", store_path=path),
        save_plan_version_payload(payload, store_path=path),
    ):
        assert result["ok"] is False
        assert result["errors"]
    assert (path.read_bytes() if path.is_file() else None) == original

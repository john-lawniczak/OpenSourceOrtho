from __future__ import annotations

import json
import sys

from orthoplan import cli
from orthoplan.validation import run_measurement_lab


def test_measurement_lab_builtin_cases_pass() -> None:
    results = run_measurement_lab()
    assert results
    assert all(result.passed for result in results)


def test_measurement_lab_can_run_one_case() -> None:
    results = run_measurement_lab("cumulative-translation")
    assert len(results) == 1
    assert results[0].case_id == "cumulative-translation"
    assert results[0].passed is True


def test_measurement_lab_reports_golden_fixture_expectations() -> None:
    results = run_measurement_lab("golden-stl-bounds")

    result = results[0]
    assert result.passed is True
    assert result.expected["max_span_mm"] == 14.0
    assert result.observed["face_count"] == 2
    assert result.tolerances["max_span_mm"] == 1e-9


def test_measurement_lab_reports_known_mm_degree_outputs() -> None:
    result = run_measurement_lab("known-mm-degree-transform")[0]

    assert result.passed is True
    assert result.expected["translate_x_mm"] == 1.0
    assert result.observed["rotate_rotation_deg"] == 5.0
    assert result.observed["rotation_renderable"] is False


def test_cli_measurement_lab_json(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "argv", ["orthoplan", "measurement-lab", "--json"])

    assert cli.main() == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload
    assert all(item["passed"] for item in payload)


def test_cli_measurement_lab_unknown_case(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "argv", ["orthoplan", "measurement-lab", "--case", "missing"])

    assert cli.main() == 2
    assert "unknown case" in capsys.readouterr().err

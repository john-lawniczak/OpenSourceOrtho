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

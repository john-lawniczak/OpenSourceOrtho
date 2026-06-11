from __future__ import annotations

import json
import sys

from orthoplan import cli
from orthoplan.validation import run_validation_benchmarks


def test_validation_benchmark_harness_emits_component_metrics() -> None:
    report = run_validation_benchmarks()

    components = {metric.component for metric in report.metrics}
    names = {metric.name for metric in report.metrics}

    assert {"segmentation", "movement", "collision-ipr", "shell-thickness"} <= components
    assert {"segmentation_dice", "segmentation_iou"} <= names
    assert "movement_translation_error" in names
    assert {"collision_ipr_precision", "collision_ipr_recall"} <= names
    assert "shell_thickness_error" in names


def test_validation_benchmark_cli_json(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "argv", ["orthoplan", "validation-benchmark", "--json"])

    assert cli.main() == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["benchmark_id"] == "synthetic-validation-v1"
    assert payload["metrics"]

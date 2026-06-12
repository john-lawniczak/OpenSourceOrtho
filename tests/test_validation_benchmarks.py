from __future__ import annotations

import json
import sys

from orthoplan import cli
from orthoplan.validation import reviewed_benchmark_corpus, run_validation_benchmarks


def test_validation_benchmark_harness_emits_component_metrics() -> None:
    report = run_validation_benchmarks()

    components = {metric.component for metric in report.metrics}
    names = {metric.name for metric in report.metrics}

    assert {"segmentation", "movement", "collision-ipr", "shell-thickness"} <= components
    assert "messy-shell" in components
    assert "benchmark-corpus" in components
    assert {"segmentation_dice", "segmentation_iou"} <= names
    assert "movement_translation_error" in names
    assert {"collision_ipr_precision", "collision_ipr_recall"} <= names
    assert {
        "collision_sample_distance",
        "collision_triangle_distance",
        "collision_triangle_delta_vs_sample",
    } <= names
    assert "shell_thickness_error" in names
    assert {"messy_shell_connected_components", "messy_shell_self_intersections"} <= names
    assert "reviewed_non_phi_corpus_cases" in names


def test_validation_benchmark_tracks_metric_deltas() -> None:
    report = run_validation_benchmarks()

    dice = next(metric for metric in report.metrics if metric.name == "segmentation_dice")
    assert report.baseline_id == "validation-benchmark-v1.2-baseline"
    assert dice.baseline_value is not None
    assert dice.delta_from_baseline == round(dice.value - dice.baseline_value, 6)


def test_reviewed_benchmark_corpus_records_non_phi_provenance() -> None:
    cases = reviewed_benchmark_corpus()

    assert cases
    case = cases[0]
    assert case.case_id == "canonical-orthocad-001"
    assert case.reviewed is True
    assert case.phi_removed is True
    assert case.consent_acknowledged is True
    assert len(case.scans) == 2
    assert {scan.arch for scan in case.scans} == {"maxillary", "mandibular"}


def test_validation_benchmark_cli_json(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "argv", ["orthoplan", "validation-benchmark", "--json"])

    assert cli.main() == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["benchmark_id"] == "validation-benchmark-v2"
    assert payload["baseline_id"] == "validation-benchmark-v1.2-baseline"
    assert payload["metrics"]
    assert payload["corpus_cases"]

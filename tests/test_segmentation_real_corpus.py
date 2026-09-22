from __future__ import annotations

import json
from pathlib import Path

from orthoplan.segmentation.heuristic import ToothSegment
from orthoplan.validation.segmentation_real_corpus import labelled_real_scan_metrics


class _StaticSegmenter:
    name = "static-perfect"
    version = "test"

    def segment(self, vertices, *, arch, tooth_values=None):
        tri = (vertices[0], vertices[1], vertices[2])
        return [ToothSegment("11", [tri], (0.2, 0.2, 0.0), 0.95)]


def _write_one_triangle_stl(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "solid tooth",
                "facet normal 0 0 1",
                "outer loop",
                "vertex 0 0 0",
                "vertex 1 0 0",
                "vertex 0 1 0",
                "endloop",
                "endfacet",
                "endsolid tooth",
            ]
        ),
        encoding="utf-8",
    )


def test_labelled_real_scan_metrics_skip_without_manifest() -> None:
    metrics = labelled_real_scan_metrics(manifest_path=None)
    by_name = {metric.name: metric for metric in metrics}

    assert by_name["labelled_real_scan_cases"].value == 0.0
    assert by_name["scored_labelled_real_scan_cases"].value == 0.0


def test_labelled_real_scan_manifest_scores_license_clear_case(tmp_path: Path) -> None:
    scan = tmp_path / "case.stl"
    labels = tmp_path / "labels.json"
    manifest = tmp_path / "manifest.json"
    _write_one_triangle_stl(scan)
    labels.write_text(json.dumps({"triangle_labels": ["11"]}), encoding="utf-8")
    manifest.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "case_id": "non-phi-001",
                        "arch": "maxillary",
                        "scan_path": "case.stl",
                        "labels_path": "labels.json",
                        "phi_removed": True,
                        "consent_acknowledged": True,
                        "commercial_use_allowed": True,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    metrics = labelled_real_scan_metrics(manifest_path=manifest, segmenter=_StaticSegmenter())
    values = {(metric.name, metric.case_id): metric.value for metric in metrics}

    assert values[("labelled_real_scan_cases", "manifest")] == 1.0
    assert values[("license_clear_labelled_real_scan_cases", "manifest")] == 1.0
    assert values[("scored_labelled_real_scan_cases", "manifest")] == 1.0
    assert values[("labelled_real_scan_triangle_label_accuracy", "non-phi-001")] == 1.0

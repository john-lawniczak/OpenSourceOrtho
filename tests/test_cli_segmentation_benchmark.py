from __future__ import annotations

import json
import sys
from pathlib import Path

from orthoplan import cli


def test_cli_segmentation_benchmark_json(monkeypatch, capsys, tmp_path: Path) -> None:
    manifest = _write_labelled_case(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "orthoplan",
            "segmentation-benchmark",
            "--manifest",
            str(manifest),
            "--min-triangle-label-accuracy",
            "0",
            "--min-region-purity",
            "0",
            "--json",
        ],
    )

    assert cli.main() == 0

    payload = json.loads(capsys.readouterr().out)
    assert len(payload["cases"]) == 1
    assert payload["cases"][0]["case_id"] == "cli-labelled-001"


def _write_labelled_case(root: Path) -> Path:
    scan = root / "case.stl"
    labels = root / "labels.json"
    manifest = root / "manifest.json"
    scan.write_text(
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
    labels.write_text(json.dumps({"triangle_labels": ["11"]}), encoding="utf-8")
    manifest.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "case_id": "cli-labelled-001",
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
    return manifest

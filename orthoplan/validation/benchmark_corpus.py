from __future__ import annotations

import json
from pathlib import Path

from orthoplan.validation.benchmark_models import BenchmarkCorpusCase, BenchmarkCorpusScan


def reviewed_benchmark_corpus() -> list[BenchmarkCorpusCase]:
    """Reviewed non-PHI scan cases available for benchmark reporting."""

    manifest_path = _repo_root() / "ui/example-scans/canonical-orthocad-001/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    scans = [
        BenchmarkCorpusScan(
            filename=scan["filename"],
            sha256=scan["sha256"],
            arch=scan["arch"],
            units=scan["units"],
            provenance=scan["provenance"],
            vertex_count=scan["vertex_count"],
            face_count=scan["face_count"],
        )
        for scan in manifest["scans"]
    ]
    return [
        BenchmarkCorpusCase(
            case_id="canonical-orthocad-001",
            source="bundled Sample Test Case manifest",
            license="project fixture; consent acknowledged in manifest",
            phi_removed=bool(manifest["phi_removed"]),
            consent_acknowledged=bool(manifest["consent_acknowledged"]),
            reviewed=True,
            notes=manifest["notes"],
            scans=scans,
        )
    ]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]

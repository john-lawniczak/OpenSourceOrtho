from __future__ import annotations

from orthoplan.datasets import SAMPLE_CASE_DIR, SAMPLE_SPECIMEN_ID

import json

from orthoplan.validation.benchmark_models import BenchmarkCorpusCase, BenchmarkCorpusScan


# Review belongs to these exact baseline assets, not to every future case visit.
_REVIEWED_SCAN_HASHES = {
    "76daf4068ec39fa2685607adc4ef50b254d275fb28d7a311af0f1dc9705e7166",
    "5e4b629904c481bf914393b4935f324599d74031c78c92f2ad2e36e637243a72",
}


def reviewed_benchmark_corpus() -> list[BenchmarkCorpusCase]:
    """Reviewed non-PHI scan cases available for benchmark reporting."""

    manifest_path = SAMPLE_CASE_DIR / "manifest.json"
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
        if scan["sha256"] in _REVIEWED_SCAN_HASHES and scan["role"] == "initial"
    ]
    return [
        BenchmarkCorpusCase(
            case_id=SAMPLE_SPECIMEN_ID,
            source="bundled Sample Test Case manifest",
            license="project fixture; consent acknowledged in manifest",
            phi_removed=bool(manifest["phi_removed"]),
            consent_acknowledged=bool(manifest["consent_acknowledged"]),
            reviewed=True,
            notes=manifest["notes"],
            scans=scans,
        )
    ]

"""Snapshot USER_ONE endpoint inputs without assuming scale or independent review."""

import base64
import hashlib
import json
from pathlib import Path
from importlib.metadata import version, PackageNotFoundError

from orthoplan.datasets import SAMPLE_CASE_DIR, SAMPLE_SPECIMEN_ID
from orthoplan.hashing import canonical_json, sha256_text
from orthoplan.region_corrections import baseline_source
from orthoplan.sample_teeth import sample_annotation, MissingPaintedSample

GENERATOR = "saved-label-refit-v1"


def endpoint_inputs(arch):
    if arch not in {"upper", "lower"}:
        raise ValueError("Choose upper or lower arch")
    display = json.loads((SAMPLE_CASE_DIR / "derived/progress-01-comparison.json").read_text())[
        "display"
    ]
    sources, corrections, bindings = [], [], []
    for visit in ["initial", "progress-01"]:
        source = baseline_source(arch, visit)
        try:
            correction, origin = sample_annotation(arch, visit)
        except MissingPaintedSample:
            correction, origin = None, "automatic-fallback"
        if visit == "initial" and correction is None:
            raise ValueError("Save baseline tooth labels before refitting")
        sources.append(
            {
                "filename": source["filename"],
                "sha256": source["sha256"],
                "rotation": display["rotation_diagonals"][source["filename"]],
                "units": source["units"],
            }
        )
        corrections.append(correction)
        bindings.append(
            {
                "visit": visit,
                "origin": origin,
                "source_sha256": source["sha256"],
                "labels_sha256": hashlib.sha256(
                    base64.b64decode(correction["labels_base64"])
                ).hexdigest()
                if correction
                else None,
            }
        )
    inputs = {
        "specimen_id": SAMPLE_SPECIMEN_ID,
        "arch": arch,
        "sources": sources,
        "annotations": bindings,
        "generator": GENERATOR,
        "reference": "whole-arch",
        "segmenter": {"name": "hybrid-arch-graph-cut", "version": "0.2.0"},
        "pipeline_sha256": pipeline_digest(),
        "dependencies": dependency_versions(),
    }
    return inputs, corrections, sha256_text(canonical_json(inputs))


def fit_summary(preview):
    teeth = preview.get("teeth", [])
    values = [t["fit"]["p90_residual"] for t in teeth if t.get("fit")]
    return {
        "regions": len(teeth),
        "fitted": sum(t["status"].startswith("estimated") for t in teeth),
        "uncertain": sum(t["status"] == "estimated-weak" for t in teeth),
        "unmatched": sum(t["status"] == "held-unmatched" for t in teeth),
        "mean_p90_residual": sum(values) / len(values) if values else None,
        "residual_denominator": len(values),
        "units": "scan units (scale unverified)",
        "motion_accuracy": None,
    }


def pipeline_digest():
    root = Path(__file__).resolve().parent
    files = [
        root / "sample_refit.py",
        root / "sample_research_inputs.py",
        *sorted((root / "longitudinal").glob("*.py")),
        *sorted((root / "segmentation").glob("*.py")),
    ]
    return sha256_text(
        canonical_json(
            {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
        )
    )


def dependency_versions():
    result = {}
    for name in ("numpy", "scipy"):
        try:
            result[name] = version(name)
        except PackageNotFoundError:
            result[name] = "unavailable"
    return result

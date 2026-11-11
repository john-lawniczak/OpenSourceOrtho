"""Compose local segmentation, whole-arch alignment, and per-tooth endpoint fits."""

from __future__ import annotations

import numpy as np

from orthoplan.evaluation.finding import (
    Finding, FindingCategory, FindingProvenance, FindingSeverity, lint_finding,
)
from orthoplan.longitudinal.corrections import correction_segments
from orthoplan.longitudinal.match_review import apply_match_overrides
from orthoplan.longitudinal.matching import region_faces, tooth_motion
from orthoplan.longitudinal.correspondence import region_assignment
from orthoplan.longitudinal.projection import project_regions
from orthoplan.longitudinal.registration import register_arches
from orthoplan.longitudinal.simulation import simulation_report
from orthoplan.segmentation.auto import load_local_segmenter
from orthoplan.segmentation.quality import evaluate_segmentation_quality


FRAME = "display-oriented-bbox-centered-source-xyz"
SCHEMA = "opensource-ortho-endpoint-motion-preview-v1"


def centered_triangles(triangles, rotation):
    oriented = np.asarray(triangles, dtype=float) * np.asarray(rotation)
    return oriented - (oriented.min(axis=(0, 1)) + oriented.max(axis=(0, 1))) / 2


def preview_advisory():
    return lint_finding(Finding(
        severity=FindingSeverity.INFO, category=FindingCategory.EDUCATION,
        provenance=FindingProvenance.MODEL,
        title="Weekly motion is an endpoint-based estimate",
        message="Tooth regions and endpoint matches are automatic drafts. Intervening weeks "
        "use assumed timing with rigid translation and rotation interpolation, not observed weekly positions. "
        "Review the boundaries, numbering, alignment, and endpoint fit before interpreting changes.",
    )).model_dump(mode="json")


def build_arch_preview(source: np.ndarray, target: np.ndarray, *, arch: str, segmenter=None, corrections=None, source_hashes=None, reference=None, matches=None):
    segmenter = segmenter or load_local_segmenter()
    corrections = corrections or [None, None]
    source_hashes = source_hashes or [None, None]
    segments = [correction_segments(correction, mesh, sha, arch) if correction else
                segmenter.segment([tuple(v) for v in mesh.reshape(-1, 3).tolist()], arch=arch)
                for mesh, correction, sha in zip((source, target), corrections, source_hashes)]
    regions = [region_faces(mesh, parts, crop_crowns=not bool(correction) and segmenter.name != "seeded-surface-graph")
               for mesh, parts, correction in zip((source, target), segments, corrections)]
    if not all(regions):
        raise ValueError("No draft tooth regions were found in an endpoint")
    registration, metrics = register_arches(source, target, reference)
    assignment, evidence = region_assignment(*regions, registration)
    projected = project_regions(source, target, regions[0], registration, regions[1], assignment, evidence=evidence)
    if corrections[1]:
        # Corrected target FDI labels explicitly replace projected matches.
        by_id = {r["tooth"]: r for r in regions[1]}
        projected = [{**by_id[r["tooth"]], "faces": by_id[r["tooth"]]["faces"].tolist(),
                      "independent_label": r["tooth"], "face_count": len(by_id[r["tooth"]]["faces"])}
                     if r["tooth"] in by_id else None for r in regions[0]]
    projected = apply_match_overrides(regions[0], regions[1], projected, matches)
    motions = [tooth_motion(region, match, registration)
               for region, match in zip(regions[0], projected)]
    return {
        "schema": SCHEMA, "frame": FRAME, "status": "estimated-unreviewed",
        "units": "source-coordinate-units-unverified", "weeks": [1, 7],
        "arch": "upper" if arch == "maxillary" else "lower",
        "method": "Hybrid/plug-in segmentation, crown-region mask, trimmed rigid ICP, "
                  "one-to-one draft assignment cross-check, projected crown correspondence, per-region rigid fit",
        "segmenter": {"name": segmenter.name, "version": segmenter.version},
        "interpolation": "linear-pivot-translation-and-shortest-quaternion-slerp",
        "source_face_count": len(source), "target_face_count": len(target),
        "target_to_source": registration.tolist(), "registration_fit": metrics,
        "reference": ("User-selected reference faces; anatomical stability is unverified." if reference
                      else "Whole-arch best fit; not stable anatomy. Global arch movement may be removed."),
        "quality_gates": [evaluate_segmentation_quality(parts, arch=arch).model_dump()
                          for parts in segments],
        "target_region_ids": [r["tooth"] for r in regions[1]],
        "match_overrides": matches, "teeth": motions, "simulation": simulation_report(source, motions),
        "advisory_findings": [preview_advisory()],
    }

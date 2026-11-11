"""Best-effort tooth-region correspondence and endpoint poses, always draft.

Segmentation quality is evidence, not a production gate on an exploratory
preview. Only absent/degenerate geometry or grossly mismatched regions are held.
"""

from __future__ import annotations

from collections import defaultdict

import numpy as np
from scipy.spatial.transform import Rotation

from orthoplan.longitudinal.match_review import reversible_fit_evidence
from orthoplan.longitudinal.correspondence import region_assignment
from orthoplan.longitudinal.rigid import fit_endpoint, surface_points, transform


def region_faces(triangles: np.ndarray, segments: list, *, crop_crowns=True) -> list[dict]:
    """Recover source face identity exactly; never match vertices between visits.

    The upper 65% of each draft region is a rough crown mask. This reduces
    gingival influence but is not a verified gingival margin. Remaining faces
    stay as a static context surface in the simulated frames.
    """
    indices = defaultdict(list)
    for index, triangle in enumerate(triangles):
        indices[tuple(triangle.reshape(-1))].append(index)
    regions = []
    for segment in segments:
        faces = []
        for triangle in segment.triangles:
            key = tuple(np.asarray(triangle).reshape(-1))
            if not indices[key]:
                raise ValueError("Segmenter returned geometry outside the source triangles")
            faces.append(indices[key].pop())
        if not faces:
            continue
        selected = np.asarray(faces, dtype=int)
        height = triangles[selected].mean(axis=1)[:, 2]
        if crop_crowns:
            selected = selected[height >= np.quantile(height, 0.35)]
        try:
            points = surface_points(triangles[selected], 1600)
        except ValueError:
            points = triangles[selected].mean(axis=1)
        regions.append({"tooth": segment.tooth_value, "faces": selected,
                        "points": points, "confidence": segment.confidence})
    return regions


def assign_regions(source: list[dict], target: list[dict], registration: np.ndarray):
    """Return feasible one-to-one matches; preserve the public mapping interface."""
    return region_assignment(source, target, registration)[0]


def tooth_motion(region: dict, target: dict | None, registration: np.ndarray) -> dict:
    pivot = region["points"].mean(axis=0)
    record = {
        "tooth": region["tooth"], "target_tooth": None,
        "source_faces": region["faces"].tolist(), "pivot": pivot.tolist(),
        "translation": [0.0, 0.0, 0.0], "quaternion_xyzw": [0.0, 0.0, 0.0, 1.0],
        "status": "held-unmatched", "segmentation_confidence": region["confidence"],
        "fit": None, "reviewed": False,
    }
    if target is None or len(region["points"]) < 6:
        return record
    points = transform(target["points"], registration)
    try:
        matrix, metrics = fit_endpoint(region["points"], points)
    except (ValueError, np.linalg.LinAlgError):
        return record
    try:
        metrics["consistency"] = reversible_fit_evidence(region["points"], points, matrix)
    except (ValueError, np.linalg.LinAlgError):
        metrics["consistency"] = {"unavailable": True}
    rotation = Rotation.from_matrix(matrix[:3, :3])
    translation = transform(pivot, matrix) - pivot
    record.update(target_tooth=target["tooth"], fit=metrics,
                  independent_target_label=target.get("independent_label"),
                  target_region_face_count=target.get("face_count"),
                  match_provenance=target.get("match_provenance", "automatic-projection"),
                  target_faces=target.get("faces"), correspondence_checks=target.get("checks"),
                  assignment_evidence=target.get("assignment_evidence"))
    # Computational sanity only, not a treatment-motion threshold.
    span = np.linalg.norm(np.ptp(region["points"], axis=0))
    if np.linalg.norm(translation) > span or rotation.magnitude() > np.pi / 3:
        return record
    consistency = metrics["consistency"]
    unstable = (consistency.get("unavailable", False) or consistency.get("round_trip_shift", 0) > span * .02
                or consistency.get("sampling_shift", 0) > span * .02
                or consistency.get("round_trip_rotation_deg", 0) > 3 or consistency.get("sampling_rotation_deg", 0) > 3)
    record.update(
        status="estimated-weak" if unstable or (target.get("assignment_evidence") or {}).get("ambiguous", False) or metrics["relative_p90"] > 0.12 or metrics["overlap"] < 0.6
        or target.get("independent_label", region["tooth"]) != region["tooth"]
        else "estimated-draft",
        translation=translation.tolist(), quaternion_xyzw=rotation.as_quat().tolist(),
        segmentation_confidence=min(region["confidence"], target["confidence"]),
    )
    return record

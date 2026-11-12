"""Reproducible known-geometry stress cases, separate from anatomical validation."""

import numpy as np
from scipy.spatial.transform import Rotation
from orthoplan.longitudinal.match_review import reversible_fit_evidence
from orthoplan.longitudinal.rigid import fit_endpoint, transform

CONDITIONS = (
    "exact-repeat",
    "noisy-repeat",
    "resampled-repeat",
    "known-motion",
    "partial-surface",
    "noisy-motion",
)


def surface(seed, count=700):
    rng = np.random.default_rng(seed)
    direction = rng.normal(size=(count, 3))
    direction /= np.linalg.norm(direction, axis=1)[:, None]
    # Analytic asymmetric shape; independent sampling never reuses correspondences.
    radius = 1 + 0.18 * direction[:, 0] * direction[:, 1] + 0.12 * direction[:, 2] ** 3
    return direction * radius[:, None] * [2.4, 1.5, 1.1]


def run_case(seed, condition):
    rng = np.random.default_rng(seed + 4000)
    source = surface(seed)
    expected = np.eye(4)
    no_motion = condition.endswith("repeat")
    if not no_motion:
        expected[:3, :3] = Rotation.from_euler("xyz", [2, -3, 5], degrees=True).as_matrix()
        expected[:3, 3] = [0.12, -0.08, 0.06]
    target = transform(
        surface(seed + 1000, 600) if condition == "resampled-repeat" else source, expected
    )
    if condition.startswith("noisy"):
        target += rng.normal(scale=0.02, size=target.shape)
    if condition == "partial-surface":
        target = target[source[:, 2] > -0.45]
    fitted, metrics = fit_endpoint(source, target)
    pivot = source.mean(axis=0)
    shift = float(np.linalg.norm(transform(pivot, fitted) - transform(pivot, expected)))
    rotation = float(
        np.degrees(Rotation.from_matrix(fitted[:3, :3] @ expected[:3, :3].T).magnitude())
    )
    return {
        "seed": seed,
        "condition": condition,
        "translation_error_mm": shift,
        "rotation_error_deg": rotation,
        "p90_surface_residual_mm": metrics["p90_residual"],
        "false_motion": bool(shift > 0.05 or rotation > 1) if no_motion else None,
        "consistency": reversible_fit_evidence(source, target, fitted),
    }


def run_stress_benchmark(seeds=range(6)):
    cases = [run_case(seed, condition) for condition in CONDITIONS for seed in seeds]
    summaries = []
    for condition in CONDITIONS:
        selected = [r for r in cases if r["condition"] == condition]
        summaries.append(
            {
                "condition": condition,
                "cases": len(selected),
                "translation_rmse_mm": float(
                    np.sqrt(np.mean([r["translation_error_mm"] ** 2 for r in selected]))
                ),
                "rotation_mean_error_deg": float(
                    np.mean([r["rotation_error_deg"] for r in selected])
                ),
                "rotation_max_error_deg": max(r["rotation_error_deg"] for r in selected),
                "false_motion_cases": sum(r["false_motion"] is True for r in selected),
            }
        )
    return {
        "schema": "ortho-motion-stress-v1",
        "kind": "synthetic",
        "units": "synthetic-mm",
        "scope": "Single-region fitting with known identity; excludes segmentation and whole-arch registration",
        "false_motion_thresholds": {"translation_mm": 0.05, "rotation_deg": 1},
        "real_accuracy": None,
        "summaries": summaries,
        "cases": cases,
    }

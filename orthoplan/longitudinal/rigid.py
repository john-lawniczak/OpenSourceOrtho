"""Deterministic rigid surface fitting for exploratory endpoint comparisons.

Coordinates retain source units. No scale fitting, deformation, anatomical
reference claim, or conversion to clinical movement axes occurs here.
Requires the optional motion-preview extra, only at artifact-generation time.
"""

from __future__ import annotations

import numpy as np
from scipy.spatial import cKDTree


def transform(points: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    return np.asarray(points) @ matrix[:3, :3].T + matrix[:3, 3]


def surface_points(triangles: np.ndarray, limit: int = 2400) -> np.ndarray:
    """Area-weighted deterministic triangle-centroid samples, avoiding STL density bias."""
    triangles = np.asarray(triangles, dtype=float)
    areas = np.linalg.norm(np.cross(triangles[:, 1] - triangles[:, 0],
                                   triangles[:, 2] - triangles[:, 0]), axis=1)
    valid = np.isfinite(triangles).all(axis=(1, 2)) & (areas > 1e-12)
    triangles, areas = triangles[valid], areas[valid]
    if len(triangles) < 6:
        raise ValueError("Too few nondegenerate surface faces for a motion estimate")
    cumulative = np.cumsum(areas)
    quantiles = (np.arange(min(limit, len(triangles))) + 0.5) / min(limit, len(triangles))
    indices = np.unique(np.searchsorted(cumulative, quantiles * cumulative[-1]))
    return triangles[indices].mean(axis=1)


def rigid_fit(source: np.ndarray, target: np.ndarray) -> np.ndarray:
    """Least-squares proper rotation + translation for *paired* points (Kabsch)."""
    if len(source) < 3 or source.shape != target.shape:
        raise ValueError("Rigid fitting needs at least three paired points")
    left, right = source.mean(axis=0), target.mean(axis=0)
    u, singular, vt = np.linalg.svd((source - left).T @ (target - right))
    if singular[1] < 1e-12:
        raise ValueError("Collinear points do not constrain a rigid fit")
    correction = np.diag([1.0, 1.0, np.linalg.det(vt.T @ u.T)])
    rotation = vt.T @ correction @ u.T
    matrix = np.eye(4)
    matrix[:3, :3] = rotation
    matrix[:3, 3] = right - rotation @ left
    return matrix


def fit_metrics(source: np.ndarray, target: np.ndarray, matrix: np.ndarray) -> dict:
    """Bidirectional residuals, in source units; not tooth-identity confidence."""
    moved = transform(source, matrix)
    forward = cKDTree(target).query(moved)[0]
    reverse = cKDTree(moved).query(target)[0]
    distances = np.concatenate([forward, reverse])
    scale = max(float(np.linalg.norm(np.ptp(source, axis=0))), 1e-9)
    return {
        "median_residual": float(np.median(distances)),
        "p90_residual": float(np.quantile(distances, 0.9)),
        "relative_p90": float(np.quantile(distances, 0.9) / scale),
        "overlap": float(np.mean(distances <= scale * 0.08)),
    }


def trimmed_icp(source, target, *, initial=None, iterations=80, keep=0.8):
    """Local point-to-point ICP with outlier trimming, never an accepted registration."""
    source, target = np.asarray(source, dtype=float), np.asarray(target, dtype=float)
    if min(len(source), len(target)) < 6 or not all(np.isfinite(p).all() for p in (source, target)):
        raise ValueError("ICP needs finite point sets with at least six samples")
    matrix = np.eye(4) if initial is None else np.asarray(initial, dtype=float).copy()
    tree = cKDTree(target)
    for _ in range(iterations):
        moved = transform(source, matrix)
        distances, indices = tree.query(moved)
        selected = np.argsort(distances, kind="stable")[:max(6, int(len(source) * keep))]
        update = rigid_fit(moved[selected], target[indices[selected]])
        matrix = update @ matrix
        if np.linalg.norm(update - np.eye(4)) < 1e-7:
            break
    return matrix, fit_metrics(source, target, matrix)


def fit_endpoint(source: np.ndarray, target: np.ndarray):
    """Choose between identity and centroid initialization by symmetric residual."""
    centered = np.eye(4)
    centered[:3, 3] = np.median(target, axis=0) - np.median(source, axis=0)
    candidates = []
    for seed in (np.eye(4), centered):
        try:
            candidates.append(trimmed_icp(source, target, initial=seed))
        except (ValueError, np.linalg.LinAlgError):
            continue
    if not candidates:
        raise ValueError("No nondegenerate endpoint fit was found")
    return min(candidates, key=lambda item: item[1]["median_residual"])

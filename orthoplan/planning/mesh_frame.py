"""Approximate per-tooth local frame from crown-surface PCA (Phase 3).

This derives a tooth-local frame from the principal axes of a segmented crown
point cloud. It is deterministic and dependency-free (no numpy), but the axes
are ordered by geometric variance and do NOT map to anatomical axes. The frame
is therefore labeled approximate and must never be presented as an anatomical or
biomechanical measurement (see ToothLocalFrame).
"""

from __future__ import annotations

from math import atan2, cos, sin

from orthoplan.model.geometry import ToothLocalFrame, Vec3

# Below this largest-variance value the point cloud is effectively a point (e.g.
# a degenerate mesh); no meaningful frame exists, so we return None rather than
# fabricate axes.
_MIN_VARIANCE = 1e-9


def _covariance(vertices: list[Vec3], centroid: Vec3) -> list[list[float]]:
    cov = [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]
    for v in vertices:
        d = (v[0] - centroid[0], v[1] - centroid[1], v[2] - centroid[2])
        for i in range(3):
            for j in range(3):
                cov[i][j] += d[i] * d[j]
    n = len(vertices)
    for i in range(3):
        for j in range(3):
            cov[i][j] /= n
    return cov


def _jacobi_eigen(a: list[list[float]]) -> tuple[list[float], list[list[float]]]:
    """Eigen-decomposition of a symmetric 3x3 matrix via Jacobi rotations.

    Returns (eigenvalues, eigenvectors) where eigenvectors[k] is the k-th unit
    eigenvector (column k).
    """
    a = [row[:] for row in a]
    v = [[1.0 if i == j else 0.0 for j in range(3)] for i in range(3)]
    for _ in range(50):
        # largest off-diagonal magnitude
        p, q, off = 0, 1, abs(a[0][1])
        for i, j in ((0, 2), (1, 2)):
            if abs(a[i][j]) > off:
                p, q, off = i, j, abs(a[i][j])
        if off < 1e-12:
            break
        if a[p][p] == a[q][q]:
            theta = 0.7853981633974483  # pi/4
        else:
            theta = 0.5 * atan2(2 * a[p][q], a[p][p] - a[q][q])
        c, s = cos(theta), sin(theta)
        for k in range(3):
            akp, akq = a[k][p], a[k][q]
            a[k][p] = c * akp + s * akq
            a[k][q] = -s * akp + c * akq
        for k in range(3):
            apk, aqk = a[p][k], a[q][k]
            a[p][k] = c * apk + s * aqk
            a[q][k] = -s * apk + c * aqk
        for k in range(3):
            vkp, vkq = v[k][p], v[k][q]
            v[k][p] = c * vkp + s * vkq
            v[k][q] = -s * vkp + c * vkq
    eigenvalues = [a[i][i] for i in range(3)]
    eigenvectors = [[v[r][col] for r in range(3)] for col in range(3)]
    return eigenvalues, eigenvectors


def _normalize(vec: list[float]) -> Vec3:
    length = (vec[0] ** 2 + vec[1] ** 2 + vec[2] ** 2) ** 0.5
    if length == 0:
        return (0.0, 0.0, 0.0)
    return (vec[0] / length, vec[1] / length, vec[2] / length)


def compute_local_frame(vertices: list[Vec3]) -> ToothLocalFrame | None:
    """Approximate PCA frame for a crown point cloud, or None if not meaningful."""
    n = len(vertices)
    if n < 3:
        return None
    centroid = (
        sum(v[0] for v in vertices) / n,
        sum(v[1] for v in vertices) / n,
        sum(v[2] for v in vertices) / n,
    )
    eigenvalues, eigenvectors = _jacobi_eigen(_covariance(vertices, centroid))
    if max(eigenvalues) < _MIN_VARIANCE:
        return None
    order = sorted(range(3), key=lambda k: eigenvalues[k], reverse=True)
    axes = tuple(_normalize(eigenvectors[k]) for k in order)
    return ToothLocalFrame(origin=centroid, axes=axes)  # type: ignore[arg-type]

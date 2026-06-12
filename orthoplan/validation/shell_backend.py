from __future__ import annotations

import hashlib

from orthoplan.aligner_shell import build_aligner_shell
from orthoplan.aligner_shell_robust import build_robust_shell, robust_shell_available
from orthoplan.model.geometry import Vec3

Triangle = tuple[Vec3, Vec3, Vec3]


def shell_backend_comparison_metrics() -> list[dict[str, float | str]]:
    """Compare pure-Python and robust shell QA on non-PHI synthetic fixtures."""

    metrics = [_availability_metric()]
    if not robust_shell_available():
        metrics.append(_skipped_metric())
        return metrics

    cases = [
        ("messy-sliver-duplicate", _messy_fixture()),
        ("independent-full-arch", _independent_full_arch_fixture()),
    ]
    for case_id, triangles in cases:
        metrics.extend(_case_metrics(case_id, triangles))
    return metrics


def _availability_metric() -> dict[str, float | str]:
    return {
        "name": "robust_backend_available",
        "value": 1.0 if robust_shell_available() else 0.0,
        "component": "shell-backend",
        "case_id": "open3d-optional-extra",
        "notes": "1 means the optional mesh-processing extra is importable in this environment.",
    }


def _skipped_metric() -> dict[str, float | str]:
    return {
        "name": "robust_backend_validation_cases",
        "value": 0.0,
        "component": "shell-backend",
        "case_id": "open3d-optional-extra",
        "notes": "Robust backend comparison skipped because Open3D is unavailable.",
    }


def _case_metrics(case_id: str, triangles: list[Triangle]) -> list[dict[str, float | str]]:
    pure = build_aligner_shell(triangles, thickness_mm=0.6)
    robust = build_robust_shell(triangles, thickness_mm=0.6)
    return [
        _metric("robust_backend_validation_cases", 1.0, case_id),
        _metric(
            "robust_vs_pure_thickness_delta",
            abs(robust.stats.measured_thickness_mm - pure.stats.measured_thickness_mm),
            case_id,
            unit="mm",
        ),
        _metric("robust_shell_self_intersections", robust.stats.self_intersection_count, case_id),
        _metric("robust_shell_nonmanifold_edges", robust.stats.nonmanifold_edge_count, case_id),
        _metric(
            "robust_shell_hash_changed_from_pure",
            1.0 if _hash(robust.triangles) != _hash(pure.triangles) else 0.0,
            case_id,
        ),
    ]


def _metric(
    name: str,
    value: float,
    case_id: str,
    *,
    unit: str = "",
) -> dict[str, float | str]:
    metric: dict[str, float | str] = {
        "name": name,
        "value": float(value),
        "component": "shell-backend",
        "case_id": case_id,
    }
    if unit:
        metric["unit"] = unit
    return metric


def _messy_fixture() -> list[Triangle]:
    quad = [
        ((0.0, 0.0, 0.0), (2.0, 0.0, 0.0), (2.0, 1.0, 0.0)),
        ((0.0, 0.0, 0.0), (2.0, 1.0, 0.0), (0.0, 1.0, 0.0)),
    ]
    duplicate = quad[0]
    inverted = (quad[1][0], quad[1][2], quad[1][1])
    sliver = ((0.0, 1.05, 0.0), (2.0, 1.05, 0.0), (2.0, 1.050001, 0.0))
    island = [
        tuple((vertex[0] + 3.0, vertex[1], vertex[2] + 0.1) for vertex in tri)  # type: ignore[misc]
        for tri in quad
    ]
    return [*quad, duplicate, inverted, sliver, *island]


def _independent_full_arch_fixture(cols: int = 20, rows: int = 10) -> list[Triangle]:
    """A deterministic arch-like mesh from a generator independent of shell code."""

    points = []
    for row in range(rows + 1):
        v = row / rows
        strip = []
        for col in range(cols + 1):
            u = (col / cols - 0.5) * 2.0
            x = u * 18.0
            y = (v - 0.5) * 12.0
            z = 0.015 * x * x + 0.08 * y + 0.35 * (1.0 - abs(u))
            strip.append((x, y, z))
        points.append(strip)

    triangles: list[Triangle] = []
    for row in range(rows):
        for col in range(cols):
            a = points[row][col]
            b = points[row][col + 1]
            c = points[row + 1][col]
            d = points[row + 1][col + 1]
            triangles.append((a, b, d))
            triangles.append((a, d, c))
    return triangles


def _hash(triangles: list[Triangle]) -> str:
    digest = hashlib.sha256()
    for tri in triangles:
        for vertex in tri:
            digest.update(f"{vertex[0]:.6f},{vertex[1]:.6f},{vertex[2]:.6f};".encode())
        digest.update(b"|")
    return digest.hexdigest()

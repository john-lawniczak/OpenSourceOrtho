"""Per-stage aligner-shell artifacts for the print package.

Builds a printable aligner shell from each stage's real reviewed geometry (see
``aligner_shell``), applying a gingival trim only when trusted CBCT-derived tooth
axes define the occlusal direction - otherwise it emits an untrimmed closed shell
rather than guessing where the gumline is (fail-closed). Shells are never built
from schematic proxy teeth.
"""

from __future__ import annotations

from math import sqrt
from pathlib import Path

from orthoplan.aligner_shell import TrimPlane, build_aligner_shell
from orthoplan.hashing import sha256_bytes
from orthoplan.model.plan import TreatmentPlan
from orthoplan.print_stl import solid_stl, stage_real_triangles

Vec3 = tuple[float, float, float]


def write_aligner_shells(
    plan: TreatmentPlan,
    output: Path,
    frames: list,
    stem: str,
    tooth_geometry: dict,
) -> tuple[list[str], list[dict], list[dict]]:
    """Write shell STLs and return (paths, artifact records, stage QA reports)."""

    settings = plan.settings.print_export
    paths: list[str] = []
    records: list[dict] = []
    reports: list[dict] = []
    trim = _gingival_trim(plan, settings.gingival_trim_margin_mm)
    for frame in frames:
        triangles = stage_real_triangles(frame.poses, tooth_geometry)
        if not triangles:
            reports.append(_skipped_report(frame.stage_index, "real reviewed geometry unavailable"))
            continue  # fail closed: no real geometry -> no shell for this stage
        try:
            shell = build_aligner_shell(
                triangles,
                thickness_mm=settings.sheet_thickness_mm,
                minimum_printable_feature_mm=settings.minimum_printable_feature_mm,
                trim=trim,
                xy_compensation_mm=settings.xy_compensation_mm,
                z_compensation_mm=settings.z_compensation_mm,
            )
        except ValueError as exc:
            reports.append(_skipped_report(frame.stage_index, str(exc), verdict="ISSUES"))
            continue
        path = output / f"{stem}-stage-{frame.stage_index:02d}-aligner-shell.stl"
        path.write_text(
            solid_stl(f"{stem}_stage_{frame.stage_index:02d}_aligner", shell.triangles),
            encoding="utf-8",
        )
        paths.append(str(path))
        record = _shell_record(path, frame.stage_index, shell.stats)
        records.append(record)
        reports.append(_completed_report(frame.stage_index, record))
    return paths, records, reports


def _shell_record(path: Path, stage_index: int, stats) -> dict:
    return {
        "filename": path.name,
        "stage_index": stage_index,
        "kind": "aligner-shell",
        "format": "stl-ascii",
        "sha256": sha256_bytes(path.read_bytes()),
        "byte_size": path.stat().st_size,
        "quality": _quality_block(stats),
        "requested_thickness_mm": stats.requested_thickness_mm,
        "measured_thickness_mm": round(stats.measured_thickness_mm, 4),
        "watertight": stats.watertight,
        "gingival_trim_applied": stats.trimmed,
    }


def _quality_block(stats) -> dict:
    failed = _failed_checks(stats)
    return {
        "verdict": "ISSUES" if failed else "CONSISTENT",
        "failed_checks": failed,
        "watertight": stats.watertight,
        "connected_components": stats.connected_components,
        "triangle_count": stats.triangle_count,
        "dropped_degenerate_input_triangles": stats.dropped_degenerate_input_triangles,
        "skinny_input_triangle_count": stats.skinny_input_triangle_count,
        "input_boundary_edge_count": stats.input_boundary_edge_count,
        "stitched_rim_triangle_count": stats.stitched_rim_triangle_count,
        "rim_closed": stats.rim_closed,
        "self_intersection_count": stats.self_intersection_count,
        "nonmanifold_edge_count": stats.nonmanifold_edge_count,
        "inner_outer_min_clearance_mm": round(stats.inner_outer_min_clearance_mm, 4),
        "minimum_printable_feature_mm": round(stats.minimum_printable_feature_mm, 4),
        "xy_compensation_mm": round(stats.xy_compensation_mm, 4),
        "z_compensation_mm": round(stats.z_compensation_mm, 4),
        "thickness_mm": {
            "requested": round(stats.requested_thickness_mm, 4),
            "mean": round(stats.measured_thickness_mm, 4),
            "min": round(stats.min_thickness_mm, 4),
            "max": round(stats.max_thickness_mm, 4),
            "p05": round(stats.p05_thickness_mm, 4),
            "p50": round(stats.p50_thickness_mm, 4),
            "p95": round(stats.p95_thickness_mm, 4),
        },
    }


def _failed_checks(stats) -> list[str]:
    """Human-readable reasons a shell is downgraded to ISSUES (empty = CONSISTENT).

    Each artifact now carries WHY it passed or failed, instead of collapsing six
    deterministic checks into an opaque CONSISTENT/ISSUES verdict. With a real
    triangle-triangle engine, any genuine self-intersection is a defect, so the
    tolerance is zero rather than the box-overlap approximation's allowance.
    """

    feature = stats.minimum_printable_feature_mm
    checks: list[str] = []
    if not stats.watertight:
        checks.append("mesh is not watertight (open boundary or nonmanifold edges)")
    if stats.nonmanifold_edge_count > 0:
        checks.append(f"nonmanifold edges: {stats.nonmanifold_edge_count}")
    if stats.connected_components != 1:
        checks.append(f"disconnected shell pieces: {stats.connected_components}")
    if not stats.rim_closed:
        checks.append("trim/boundary rim is not fully closed")
    if stats.self_intersection_count > 0:
        checks.append(f"self-intersecting triangles: {stats.self_intersection_count}")
    if stats.min_thickness_mm < feature:
        checks.append(
            f"min wall thickness {stats.min_thickness_mm:.3f} mm below "
            f"minimum printable feature {feature:.3f} mm"
        )
    if stats.inner_outer_min_clearance_mm < feature:
        checks.append(
            f"inner/outer clearance {stats.inner_outer_min_clearance_mm:.3f} mm below "
            f"minimum printable feature {feature:.3f} mm"
        )
    return checks


def _completed_report(stage_index: int, record: dict) -> dict:
    return {
        "stage_index": stage_index,
        "verdict": record["quality"]["verdict"],
        "filename": record["filename"],
        "quality": record["quality"],
    }


def _skipped_report(stage_index: int, reason: str, *, verdict: str = "NOT_APPLICABLE") -> dict:
    return {
        "stage_index": stage_index,
        "verdict": verdict,
        "reason": f"Aligner shell not generated: {reason}; model-only export remains available.",
    }


def _gingival_trim(plan: TreatmentPlan, margin_mm: float) -> TrimPlane | None:
    """A gingival trim plane derived from trusted tooth axes, or None.

    Fail-closed: without trusted CBCT-derived occlusal axes we do not know which
    way is gingival, so we return None (no trim) instead of cutting blindly.
    """

    anatomy = plan.derived_anatomy
    if anatomy is None:
        return None
    axes = [a.direction for a in anatomy.tooth_axes if a.trusted]
    origins = [a.origin_mm for a in anatomy.tooth_axes if a.trusted]
    if not axes:
        return None
    occlusal = _normalize(_mean(axes))
    if occlusal is None:
        return None
    # Project axis origins onto the occlusal direction; the gingival end is the
    # minimum projection. Keep everything from (min + margin) toward occlusal.
    gingival_origin = min(origins, key=lambda p: _dot(p, occlusal))
    point = tuple(gingival_origin[i] + occlusal[i] * margin_mm for i in range(3))
    return TrimPlane(point=point, normal=occlusal)  # type: ignore[arg-type]


def _dot(a: Vec3, b: Vec3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _mean(vectors: list[Vec3]) -> Vec3:
    n = len(vectors)
    return (
        sum(v[0] for v in vectors) / n,
        sum(v[1] for v in vectors) / n,
        sum(v[2] for v in vectors) / n,
    )


def _normalize(v: Vec3) -> Vec3 | None:
    length = sqrt(_dot(v, v))
    if length == 0:
        return None
    return (v[0] / length, v[1] / length, v[2] / length)

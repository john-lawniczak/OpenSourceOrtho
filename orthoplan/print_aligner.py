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
) -> tuple[list[str], list[dict]]:
    """Write a shell STL per stage that has real geometry. Returns (paths, records)."""

    settings = plan.settings.print_export
    paths: list[str] = []
    records: list[dict] = []
    trim = _gingival_trim(plan, settings.gingival_trim_margin_mm)
    for frame in frames:
        triangles = stage_real_triangles(frame.poses, tooth_geometry)
        if not triangles:
            continue  # fail closed: no real geometry -> no shell for this stage
        try:
            shell = build_aligner_shell(
                triangles, thickness_mm=settings.sheet_thickness_mm, trim=trim
            )
        except ValueError:
            continue
        path = output / f"{stem}-stage-{frame.stage_index:02d}-aligner-shell.stl"
        path.write_text(
            solid_stl(f"{stem}_stage_{frame.stage_index:02d}_aligner", shell.triangles),
            encoding="utf-8",
        )
        paths.append(str(path))
        records.append({
            "filename": path.name,
            "stage_index": frame.stage_index,
            "kind": "aligner-shell",
            "format": "stl-ascii",
            "sha256": sha256_bytes(path.read_bytes()),
            "byte_size": path.stat().st_size,
            "requested_thickness_mm": shell.stats.requested_thickness_mm,
            "measured_thickness_mm": round(shell.stats.measured_thickness_mm, 4),
            "watertight": shell.stats.watertight,
            "gingival_trim_applied": shell.stats.trimmed,
        })
    return paths, records


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

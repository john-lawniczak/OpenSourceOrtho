"""Stage STL geometry generation for the print package.

Split from ``print_package`` by responsibility: this module turns plan/pose data
into STL triangles (real per-tooth vertices for reviewed segmentation, labeled
schematic proxies otherwise); ``print_package`` handles packaging, hashing,
manifest, zip, and email. Keeping geometry here keeps both files reviewable.
"""

from __future__ import annotations

from pathlib import Path

from orthoplan.io.stl_import import Vec3
from orthoplan.mesh_geometry import reviewed_fragment_triangles
from orthoplan.model.assets import BoundingBox
from orthoplan.model.plan import TreatmentPlan


def build_tooth_geometry(
    plan: TreatmentPlan, workspace: str | Path | None
) -> dict[str, dict]:
    """Per-tooth export geometry, real-vertex when reviewed, proxy otherwise.

    Returns a dict keyed by FDI value. Each entry has ``mode`` in
    {``mesh-vertices``, ``mesh-bounds-proxy``} plus the data needed to emit it.
    Real vertices are used ONLY for reviewed links whose fragment STL resolves;
    everything else is a labeled schematic proxy box (fail-closed).
    """

    assets = {asset.id: asset for asset in plan.mesh_assets}
    assets.update({scan.asset.id: scan.asset for scan in plan.scans})
    geometry: dict[str, dict] = {}
    for link in plan.tooth_meshes:
        asset = assets.get(link.mesh_asset_id)
        if asset is None or asset.bounds is None:
            continue
        triangles = reviewed_fragment_triangles(link, workspace=workspace)
        if triangles is not None:
            geometry[link.tooth.value] = {
                "mode": "mesh-vertices",
                "source": f"segmented-mesh-vertices:{asset.id}",
                "asset_id": asset.id,
                "sha256": asset.sha256,
                "triangles": triangles,
            }
        else:
            geometry[link.tooth.value] = {
                "mode": "mesh-bounds-proxy",
                "source": f"segmented-mesh-bounds:{asset.id}",
                "asset_id": asset.id,
                "sha256": asset.sha256,
                "box_size": _box_size_from_bounds(asset.bounds),
            }
    return geometry


def _box_size_from_bounds(bounds: BoundingBox) -> tuple[float, float, float]:
    sizes = [
        max(bounds.max_xyz[index] - bounds.min_xyz[index], 0.5)
        for index in range(3)
    ]
    return (sizes[0], sizes[1], sizes[2])


def frame_to_stl(
    plan_id: str,
    stage_index: int,
    poses: list,
    tooth_geometry: dict,
) -> tuple[str, list[dict]]:
    triangles: list[tuple[tuple[float, float, float], ...]] = []
    geometry_sources: list[dict] = []
    for index, pose in enumerate(poses):
        geom = tooth_geometry.get(pose.tooth.value)
        delta = (pose.translate_x_mm, pose.translate_y_mm, pose.translate_z_mm)
        if geom and geom["mode"] == "mesh-vertices":
            triangles.extend(_translate_triangles(geom["triangles"], delta))
            geometry_sources.append(
                {"tooth": pose.tooth.value, "source": geom["source"], "mode": "mesh-vertices"}
            )
            continue
        # Proxy fallback: lay the tooth out on a schematic grid sized by bounds
        # (or a fixed schematic box when no segmented bounds exist).
        cx = (index % 8) * 4.0 + delta[0]
        cy = (index // 8) * 5.0 + delta[1]
        cz = delta[2]
        source = geom["source"] if geom else "schematic-stage-proxy"
        size = geom["box_size"] if geom else (2.4, 3.2, 1.8)
        triangles.extend(_box_triangles(cx, cy, cz, *size))
        geometry_sources.append(
            {
                "tooth": pose.tooth.value,
                "source": source,
                "mode": "mesh-bounds-proxy" if geom else "schematic-proxy",
                "center_xyz_mm": [cx, cy, cz],
                "size_xyz_mm": list(size),
            }
        )
    return _stl_text(plan_id, stage_index, triangles), geometry_sources


def stage_real_triangles(poses: list, tooth_geometry: dict) -> list[tuple[Vec3, Vec3, Vec3]]:
    """Translated triangles for ONLY the real-mesh (reviewed) teeth in a stage.

    Aligner shells are built from real geometry only; proxy teeth are excluded so
    a shell is never generated around a schematic box.
    """

    triangles: list[tuple[Vec3, Vec3, Vec3]] = []
    for pose in poses:
        geom = tooth_geometry.get(pose.tooth.value)
        if not geom or geom["mode"] != "mesh-vertices":
            continue
        delta = (pose.translate_x_mm, pose.translate_y_mm, pose.translate_z_mm)
        triangles.extend(_translate_triangles(geom["triangles"], delta))
    return triangles


def _translate_triangles(
    triangles: list[tuple[Vec3, Vec3, Vec3]], delta: tuple[float, float, float]
) -> list[tuple[Vec3, Vec3, Vec3]]:
    dx, dy, dz = delta
    return [
        tuple((v[0] + dx, v[1] + dy, v[2] + dz) for v in tri)  # type: ignore[misc]
        for tri in triangles
    ]


def _stl_text(plan_id: str, stage_index: int, triangles: list) -> str:
    return solid_stl(f"{plan_id}_stage_{stage_index:02d}", triangles)


def solid_stl(name: str, triangles: list) -> str:
    """ASCII STL for a named solid from a triangle list.

    Each facet carries its real unit outward normal computed from the triangle
    winding (right-hand rule), not a placeholder ``0 0 0``. Many slicers recover
    the normal from winding, but strict CAD/validation tools treat zero-length
    facet normals as malformed, so emitting the true normal keeps the export
    spec-correct and unambiguous.
    """

    lines = [f"solid {name}"]
    for tri in triangles:
        nx, ny, nz = _facet_normal(tri)
        lines.extend(
            [
                f"  facet normal {nx:.6f} {ny:.6f} {nz:.6f}",
                "    outer loop",
                f"      vertex {tri[0][0]:.6f} {tri[0][1]:.6f} {tri[0][2]:.6f}",
                f"      vertex {tri[1][0]:.6f} {tri[1][1]:.6f} {tri[1][2]:.6f}",
                f"      vertex {tri[2][0]:.6f} {tri[2][1]:.6f} {tri[2][2]:.6f}",
                "    endloop",
                "  endfacet",
            ]
        )
    lines.append(f"endsolid {name}")
    return "\n".join(lines) + "\n"


def _facet_normal(tri: tuple[Vec3, Vec3, Vec3]) -> Vec3:
    """Unit outward normal from triangle winding; (0,0,0) if degenerate."""

    ax, ay, az = tri[0]
    bx, by, bz = tri[1]
    cx, cy, cz = tri[2]
    ux, uy, uz = bx - ax, by - ay, bz - az
    vx, vy, vz = cx - ax, cy - ay, cz - az
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    length = (nx * nx + ny * ny + nz * nz) ** 0.5
    if length == 0:
        return (0.0, 0.0, 0.0)
    return (nx / length, ny / length, nz / length)


def _box_triangles(cx: float, cy: float, cz: float, sx: float, sy: float, sz: float):
    x0, x1 = cx - sx / 2, cx + sx / 2
    y0, y1 = cy - sy / 2, cy + sy / 2
    z0, z1 = cz - sz / 2, cz + sz / 2
    v = [
        (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
        (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1),
    ]
    faces = [
        (0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1),
        (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0),
    ]
    tris = []
    for a, b, c, d in faces:
        tris.append((v[a], v[b], v[c]))
        tris.append((v[a], v[c], v[d]))
    return tris

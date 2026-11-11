"""Local two-visit fitting, bounded by the geometry worker and registered inputs."""

import base64
import hashlib
from pathlib import Path
import numpy as np
from orthoplan.io.mesh_import import read_mesh_geometry
from orthoplan.io.scan_reference import resolve_scan_path
from orthoplan.longitudinal.artifact import pack_face_labels
from orthoplan.longitudinal.preview import build_arch_preview, centered_triangles


def _scan(record, workspace, ui_dir):
    path = resolve_scan_path(record.get("reference"), workspace=workspace, ui_dir=ui_dir.resolve())
    if path is None or path.suffix.lower() != ".stl":
        raise ValueError("Choose a registered or published STL scan")
    raw = path.read_bytes()
    rotation = record.get("rotation", [1, 1, 1])
    if len(rotation) != 3 or any(n not in [-1, 1] for n in rotation) or np.prod(rotation) != 1:
        raise ValueError("Choose a proper display orientation")
    _, vertices = read_mesh_geometry(path)
    triangles = np.asarray(vertices, dtype=float).reshape(-1, 3, 3)
    if len(triangles) < 6 or not np.isfinite(triangles).all():
        raise ValueError("Scan must contain finite surface triangles")
    return centered_triangles(triangles, rotation), {
        "filename": Path(record.get("filename", path.name)).name,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "rotation": rotation,
    }


def _reference(corrections, teeth):
    if not teeth:
        return None
    if not all(corrections):
        raise ValueError("Reference tooth selection requires corrected labels on both visits")
    result = {}
    for key, record in zip(("source_faces", "target_faces"), corrections):
        labels = np.frombuffer(
            base64.b64decode(record["labels_base64"], validate=True), dtype=np.uint8
        )
        if any(int(tooth) not in labels for tooth in teeth):
            raise ValueError("A reference tooth is missing from corrected labels")
        result[key] = np.flatnonzero(np.isin(labels, [int(t) for t in teeth])).tolist()
    return result


def motion_payload(payload, *, workspace, ui_dir):
    try:
        if payload.get("arch") not in ["upper", "lower"]:
            raise ValueError("Identify the arch")
        if (
            payload.get("units") not in ["mm", "cm", "in"]
            or payload.get("units_confirmed") is not True
        ):
            raise ValueError("Confirm that both scans use the same declared units")
        scans = payload.get("scans", [])
        corrections = payload.get("corrections") or [None, None]
        if len(scans) != 2 or len(corrections) != 2:
            raise ValueError("Provide exactly two visits and their optional correction files")
        loaded = [_scan(scan, workspace, ui_dir) for scan in scans]
        sources = [item[1] for item in loaded]
        segmenter = None
        if payload.get("segmenter") == "surface-graph":
            from orthoplan.segmentation.surface_graph import SurfaceGraphSegmenter
            segmenter = SurfaceGraphSegmenter()
        elif payload.get("segmenter", "active") != "active":
            raise ValueError("Unknown segmentation backend")
        preview = build_arch_preview(
            *[item[0] for item in loaded],
            arch="maxillary" if payload["arch"] == "upper" else "mandibular",
            segmenter=segmenter, corrections=corrections,
            source_hashes=[s["sha256"] for s in sources],
            reference=_reference(corrections, payload.get("reference_teeth")),
            matches=payload.get("matches"),
        )
        preview.update(
            specimen_id="local-two-visit",
            sources=sources,
            units_confirmation={"unit": payload["units"], "provenance": "user-declared-same-scale"},
            corrections=[
                {"supplied": bool(c), "boundaries_reviewed": bool(c and c.get("reviewed"))}
                for c in corrections
            ],
        )
        pack_face_labels(preview)
        return {"ok": True, "preview": preview}
    except (ValueError, TypeError, KeyError, OSError) as exc:
        return {"ok": False, "errors": [str(exc)]}

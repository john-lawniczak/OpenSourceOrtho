"""Reproduce exact-coordinate mesh topology checks for the canonical scans.

Requires NumPy. No repair, tolerance welding, unit conversion, or registration.
"""

import hashlib
import json
from pathlib import Path
import struct
import sys

import numpy as np


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from orthoplan.datasets import SAMPLE_CASE_DIR as CASE
TRIANGLE = np.dtype([("normal", "<f4", (3,)), ("vertices", "<f4", (3, 3)),
                     ("attribute", "<u2")])


def component_sizes(edges, vertex_count):
    parent = np.arange(vertex_count)
    sizes = np.ones(vertex_count, dtype=int)

    def root(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    for a, b in edges:
        a, b = root(a), root(b)
        if a != b:
            if sizes[a] < sizes[b]:
                a, b = b, a
            parent[b] = a
            sizes[a] += sizes[b]
    return sorted(sizes[parent == np.arange(vertex_count)].tolist(), reverse=True)


def inspect(scan):
    raw = (CASE / scan["filename"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == scan["sha256"], "Scan hash mismatch"
    count = struct.unpack_from("<I", raw, 80)[0]
    assert len(raw) == 84 + 50 * count, "Binary STL size mismatch"
    triangles = np.frombuffer(raw, dtype=TRIANGLE, offset=84)["vertices"].astype(float)
    if not np.isfinite(triangles).all():
        raise ValueError("Non-finite scan geometry")
    points, faces = np.unique(triangles.reshape(-1, 3), axis=0, return_inverse=True)
    faces = faces.reshape(-1, 3)
    areas = np.linalg.norm(np.cross(triangles[:, 1] - triangles[:, 0],
                                    triangles[:, 2] - triangles[:, 0]), axis=1) / 2
    edges = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    edges.sort(axis=1)
    edges, counts = np.unique(edges, axis=0, return_counts=True)
    return {
        "filename": scan["filename"], "sha256": scan["sha256"],
        "finite_coordinates": True, "face_count": len(faces),
        "unique_vertices": len(points), "zero_area_faces": int((areas == 0).sum()),
        "duplicate_faces": len(faces) - len(np.unique(np.sort(faces, axis=1), axis=0)),
        "boundary_edges": int((counts == 1).sum()),
        "edges_with_more_than_two_incident_faces": int((counts > 2).sum()),
        "connected_component_vertex_counts": component_sizes(edges, len(points)),
    }


def main():
    manifest = json.loads((CASE / "manifest.json").read_text())
    report = {
        "schema": "opensource-ortho-scan-topology-v1",
        "specimen_id": manifest["specimen_id"],
        "generator": "tools/check_sample_topology.py",
        "method": "Exact-coordinate vertex deduplication; undirected edge incidence and connectivity; float64 triangle areas",
        "input_geometry_modified": False,
        "scans": [inspect(scan) for scan in manifest["scans"]],
        "not_assessed": ["self-intersections", "scanner accuracy", "complete anatomical coverage",
                         "bite accuracy", "physical scale", "cross-time registration"],
        "interpretation": "Topology inventory only. Open boundary edges establish that these are not closed surfaces; edge count alone does not measure scan accuracy or locate missing anatomy.",
    }
    (CASE / "derived/scan-topology.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()

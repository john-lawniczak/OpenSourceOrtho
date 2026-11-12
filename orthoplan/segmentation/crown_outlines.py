"""Conservative face labels inside explicit scan-coordinate crown outlines."""
import numpy as np
from scipy.sparse.csgraph import connected_components

from orthoplan.segmentation.topology import face_graph


def inside_polygon(points, polygon):
    """Ray crossing for XY points; no inferred tooth identity or geometry edits."""
    result = np.zeros(points.shape[:-1], dtype=bool)
    vertices = np.asarray(polygon, dtype=float)
    for a, b in zip(vertices, np.roll(vertices, 1, axis=0)):
        crossing = (a[1] > points[..., 1]) != (b[1] > points[..., 1])
        slope = (b[0] - a[0]) / (b[1] - a[1] + 1e-100)
        result ^= crossing & (points[..., 0] < (points[..., 1] - a[1]) * slope + a[0])
    return result


def separate_crowns(triangles, prior_labels, crowns):
    """Keep a single surface component per crown; contested faces stay context."""
    mesh = np.asarray(triangles, dtype=float)
    prior = np.asarray(prior_labels)
    if mesh.shape != (len(prior), 3, 3) or not np.isfinite(mesh).all():
        raise ValueError("Expected finite source triangles matching prior face labels")
    labels = np.zeros(len(mesh), dtype=np.uint8)
    owners = np.zeros(len(mesh), dtype=np.uint16)
    for crown in crowns:
        # All three corners must be inside; never extend onto prior context/base.
        mask = inside_polygon(mesh[:, :, :2], crown["outline_xy"]).all(axis=1) & (prior != 0)
        labels[mask] = crown["fdi"]
        owners += mask
    contested = owners > 1
    labels[contested] = 0
    graph = face_graph(mesh)
    edges = graph.tocoo()
    crossing = (labels[edges.row] != labels[edges.col]) & (labels[edges.row] != 0) & (labels[edges.col] != 0)
    buffer_faces = np.unique(np.r_[edges.row[crossing], edges.col[crossing]])
    labels[buffer_faces] = 0
    cleanup = {}
    for crown in crowns:
        tooth = crown["fdi"]
        faces = np.flatnonzero(labels == tooth)
        if not len(faces):
            raise ValueError(f"No connected crown candidate for {tooth}")
        count, components = connected_components(graph[faces][:, faces])
        sizes = np.bincount(components)
        discarded = faces[components != sizes.argmax()]
        labels[discarded] = 0
        cleanup[tooth] = {"components_before_cleanup": int(count), "stray_faces_removed": len(discarded)}
    audit = {"overlapping_outline_faces_left_unlabeled": int(contested.sum()),
             "contact_buffer_faces_left_unlabeled": len(buffer_faces), "per_tooth_cleanup": cleanup}
    return labels, graph, audit


def measure_crowns(triangles, labels, graph, crowns, expected_widths):
    """Report projected widths, not clinical caliper measurements of tooth size."""
    records = []
    centers = np.asarray([c["seed_xy"] for c in crowns])
    for i, crown in enumerate(crowns):
        tooth = crown["fdi"]
        faces = np.flatnonzero(labels == tooth)
        tangent = centers[min(i + 1, len(crowns) - 1)] - centers[max(i - 1, 0)]
        tangent /= np.linalg.norm(tangent)
        vertices = triangles[faces].reshape(-1, 3)
        projections = vertices[:, :2] @ tangent
        low, high = expected_widths[str(tooth % 10)]
        width = float(np.quantile(projections, .98) - np.quantile(projections, .02))
        count = connected_components(graph[faces][:, faces], return_labels=False)
        flags = ["Draft contact/gum boundaries need surface review", "Width is a projected mask estimate"]
        if width < low:
            flags.append("Below supplied range: conservative mask or tooth rotation may underestimate width")
        if width > high:
            flags.append("Above supplied range: inspect distal/gingival extent and tangent orientation")
        if width > high * 1.75:
            flags.append("Possible merged region: substantially exceeds supplied width")
        records.append({"fdi": tooth, "face_count": len(faces), "connected_components": int(count),
                        "estimated_width_mm": round(width, 2),
                        "full_projected_span_mm": round(float(np.ptp(projections)), 2),
                        "user_reference_width_mm": [low, high], "within_reference_range": low <= width <= high,
                        "centroid_xyz": triangles[faces].mean(axis=(0, 1)).tolist(), "flags": flags})
    return records

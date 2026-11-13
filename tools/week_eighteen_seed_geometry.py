"""Rigid draft-label transfer across scanner frames; never reconstruct a surface."""
import itertools

import numpy as np
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

from orthoplan.longitudinal.projection import correspondence_mask
from orthoplan.longitudinal.rigid import surface_points, transform, trimmed_icp
from orthoplan.segmentation.topology import face_graph


def fit_crowns(source, target, labels, *, wide=False):
    """Search proper PCA rotations; lower model bases also need translated starts."""
    a = surface_points(source[labels != 0], 2200 if wide else 3500)
    b = surface_points(target, 10000)
    axes = [np.linalg.eigh(np.cov(points.T))[1][:, ::-1] for points in (a, b)]
    offsets = [(0, 0)]
    if wide:
        offsets += [(0, -12), (0, 12), (1, -12), (1, 12), (2, -12), (2, 12), (2, -24), (2, 24)]
    tree, candidates = cKDTree(b), []
    for perm in itertools.permutations(range(3)):
        for signs in itertools.product([-1, 1], repeat=3):
            rotation = axes[1] @ np.eye(3)[:, perm] @ np.diag(signs) @ axes[0].T
            if np.linalg.det(rotation) < 0:
                continue
            for axis, offset in offsets:
                initial = np.eye(4)
                initial[:3, :3] = rotation
                initial[:3, 3] = np.median(b, axis=0) - rotation @ np.median(a, axis=0) + axes[1][:, axis] * offset
                fitted, metrics = trimmed_icp(a, b, initial=initial, iterations=45 if wide else 60, keep=.85)
                distance = tree.query(transform(a, fitted))[0]
                candidates.append((float(np.quantile(distance, .8)), fitted, metrics))
    candidates.sort(key=lambda item: item[0])
    score, matrix, metrics = candidates[0]
    limit = float(np.linalg.norm(np.ptp(a, axis=0)) * .025)
    if score > limit:
        raise ValueError(f"Crown fit remains weak ({score:.3f} > {limit:.3f} source units); inspect alignment before seeding")
    return matrix, {"source_crown_p80_residual": score, "residual_limit": limit,
                    "bidirectional_fit": metrics, "candidate_scores": [item[0] for item in candidates],
                    "method": "Proper PCA rotation starts, optional translated starts, trimmed rigid ICP; no scale fitting"}


def project_crowns(source, target, labels, matrix, absent=()):
    """Leave unmatched, boundary-contact and disconnected fragments unlabeled."""
    nearest, valid, checks = correspondence_mask(source, target, np.linalg.inv(matrix), max_distance=1.8, min_normal=.5)
    result = np.where(valid, labels[nearest], 0).astype(np.uint8)
    result[np.isin(result, list(absent))] = 0
    graph = face_graph(target)
    edges = graph.tocoo()
    crossing = (result[edges.row] != result[edges.col]) & (result[edges.row] != 0) & (result[edges.col] != 0)
    contact = np.unique(np.r_[edges.row[crossing], edges.col[crossing]])
    result[contact] = 0
    regions = []
    for tooth in sorted(set(labels) - {0}):
        faces = np.flatnonzero(result == tooth)
        removed = 0
        if len(faces):
            _, components = connected_components(graph[faces][:, faces])
            discarded = faces[components != np.bincount(components).argmax()]
            result[discarded] = 0
            removed = len(discarded)
        regions.append({"tooth": int(tooth), "faces": int((result == tooth).sum()), "discarded_fragment_faces": removed})
    return result, {"correspondence_checks": checks, "contact_buffer_faces": len(contact), "teeth": regions}

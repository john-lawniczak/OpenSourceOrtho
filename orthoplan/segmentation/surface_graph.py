"""Optional surface-connected draft refinement of hybrid arch seeds."""
from collections import defaultdict
import numpy as np
from orthoplan.segmentation.auto import HybridArchSegmenter
from orthoplan.segmentation.heuristic import ToothSegment, default_arch_order
from orthoplan.segmentation.topology import propagate_seeds

# Compactness scales as expected_radius / (expected_radius + gyration), mirroring
# orthoplan.validation.segmentation_compactness (kept as a separate small copy,
# not an import, so segmentation code never depends on the validation layer -
# the same one-way-dependency reason orthoplan/segmentation/quality.py keeps its
# own private copy instead of importing it).
_GYRATION_WEIGHT = 1.0


class SurfaceGraphSegmenter:
    name = 'seeded-surface-graph'
    version = '0.2.0'

    def segment(self, vertices, *, arch, tooth_values=None):
        triangles = np.asarray(vertices, dtype=float).reshape(-1, 3, 3)
        drafts = HybridArchSegmenter().segment(vertices, arch=arch, tooth_values=tooth_values)
        if not drafts:
            return []
        labels = draft_face_labels(triangles, drafts)
        refined = refine_draft_labels(triangles, labels)
        expected_count = len(tooth_values) if tooth_values else len(default_arch_order(arch))
        regions = {}
        for draft in drafts:
            faces = triangles[refined == int(draft.tooth_value)]
            if len(faces):
                regions[draft.tooth_value] = faces
        confidences = _region_confidences(regions, expected_count=expected_count)
        result = []
        for draft in drafts:
            faces = regions.get(draft.tooth_value)
            if faces is None:
                continue
            # A region's confidence reflects how cleanly it separated from its
            # neighbours (compactness), never more than the upstream draft's own
            # confidence - refinement must not manufacture certainty the draft
            # label itself did not have.
            confidence = min(draft.confidence, confidences[draft.tooth_value])
            result.append(ToothSegment(draft.tooth_value, [tuple(map(tuple, f)) for f in faces],
                                       tuple(faces.mean(axis=(0, 1))), confidence))
        return result


def _region_confidences(regions, *, expected_count):
    """Per-tooth confidence from spatial tightness (no ground truth needed).

    A region the size of one crown scores near 0.5; a region sprawling across
    several crowns scores toward 0. Mirrors the intrinsic compactness metric
    used to gate this candidate (see module docstring), applied per-call since
    "expected crown radius" depends on the SAME call's own arch footprint.
    """

    if not regions:
        return {}
    all_centers = np.concatenate([faces.mean(axis=1) for faces in regions.values()])
    xs, ys = all_centers[:, 0], all_centers[:, 1]
    diagonal = float(np.hypot(xs.max() - xs.min(), ys.max() - ys.min()))
    expected_radius = diagonal / max(expected_count, 1) / 2.0
    result = {}
    for tooth, faces in regions.items():
        centers = faces.mean(axis=1)
        centroid = centers.mean(axis=0)
        gyration = float(np.sqrt(np.mean(np.sum((centers[:, :2] - centroid[:2]) ** 2, axis=1))))
        denom = expected_radius + _GYRATION_WEIGHT * gyration
        result[tooth] = expected_radius / denom if denom > 0 else 1.0
    return result


def draft_face_labels(triangles, drafts):
    indices = defaultdict(list)
    for i, face in enumerate(triangles):
        indices[tuple(face.reshape(-1))].append(i)
    labels = np.zeros(len(triangles), dtype=int)
    for draft in drafts:
        for face in draft.triangles:
            matches = indices[tuple(np.asarray(face).reshape(-1))]
            if not matches:
                raise ValueError('Draft returned unknown or multiply owned geometry')
            labels[matches.pop()] = int(draft.tooth_value)
    return labels


def refine_draft_labels(triangles, labels):
    centers = triangles.mean(axis=1)
    seeds = np.zeros(len(labels), dtype=int)
    allowed = np.zeros(len(labels), dtype=bool)
    for tooth in sorted(set(labels)-{0}):
        faces = np.flatnonzero(labels == tooth)
        height = centers[faces, 2]
        crown = faces[height >= np.quantile(height, .35)]
        allowed[crown] = True
        core = crown[np.argsort(np.linalg.norm(centers[crown]-np.median(centers[crown], axis=0), axis=1))[:max(1, len(crown)//30)]]
        seeds[core] = tooth
    return propagate_seeds(triangles, seeds, allowed)

"""Optional surface-connected draft refinement of hybrid arch seeds."""
from collections import defaultdict
import numpy as np
from orthoplan.segmentation.auto import HybridArchSegmenter
from orthoplan.segmentation.heuristic import ToothSegment
from orthoplan.segmentation.topology import propagate_seeds


class SurfaceGraphSegmenter:
    name = 'seeded-surface-graph'
    version = '0.1.0'

    def segment(self, vertices, *, arch, tooth_values=None):
        triangles = np.asarray(vertices, dtype=float).reshape(-1, 3, 3)
        drafts = HybridArchSegmenter().segment(vertices, arch=arch, tooth_values=tooth_values)
        if not drafts:
            return []
        labels = draft_face_labels(triangles, drafts)
        refined = refine_draft_labels(triangles, labels)
        result = []
        for draft in drafts:
            faces = triangles[refined == int(draft.tooth_value)]
            if not len(faces):
                continue
            result.append(ToothSegment(draft.tooth_value, [tuple(map(tuple, f)) for f in faces],
                                       tuple(faces.mean(axis=(0, 1))), min(draft.confidence, 0.5)))
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

"""Keep cross-visit region identities stable when independent draft cuts disagree.

Transfer the baseline's draft crown masks to the registered target by nearest
surface location. This is a geometric correspondence proposal, not a verified
anatomical tooth map. Each target face belongs to at most one source region.
"""

import numpy as np
from scipy.spatial import cKDTree

from orthoplan.longitudinal.rigid import surface_points, transform


def project_regions(source, target, regions, registration, independent, assignment):
    owners = np.zeros(len(source), dtype=np.int16)
    for index, region in enumerate(regions, 1):
        owners[region["faces"]] = index
    nearest = cKDTree(source.mean(axis=1)).query(transform(target.mean(axis=1), registration))[1]
    projected = owners[nearest]
    result = []
    for index, region in enumerate(regions, 1):
        faces = np.flatnonzero(projected == index)
        if len(faces) < 6:
            result.append(None)
            continue
        candidate = independent[assignment[index - 1]] if index - 1 in assignment else None
        try:
            points = surface_points(target[faces], 1600)
        except ValueError:
            result.append(None)
            continue
        result.append({
            "tooth": region["tooth"], "points": points,
            "confidence": min(region["confidence"], candidate["confidence"]) if candidate else 0.0,
            "independent_label": candidate["tooth"] if candidate else None,
            "face_count": len(faces),
        })
    return result

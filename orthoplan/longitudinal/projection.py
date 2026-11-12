"""Keep cross-visit region identities stable when independent draft cuts disagree.

Transfer the baseline's draft crown masks to the registered target by nearest
surface location. This is a geometric correspondence proposal, not a verified
anatomical tooth map. Each target face belongs to at most one source region.
"""

import numpy as np
from scipy.spatial import cKDTree

from orthoplan.longitudinal.rigid import surface_points, transform


def correspondence_mask(source, target, registration, *, max_distance=None, min_normal=0.3):
    a, b = source.mean(axis=1), transform(target.mean(axis=1), registration)
    distance, nearest = cKDTree(a).query(b)
    reverse = cKDTree(b).query(a)[1]
    cycle = np.linalg.norm(b - b[reverse[nearest]], axis=1)
    normals = []
    for mesh in (source, target):
        n = np.cross(mesh[:, 1] - mesh[:, 0], mesh[:, 2] - mesh[:, 0])
        normals.append(n / np.maximum(np.linalg.norm(n, axis=1)[:, None], 1e-12))
    agreement = np.abs(np.sum(normals[0][nearest] * (normals[1] @ registration[:3, :3].T), axis=1))
    limit = float(max_distance) if max_distance is not None else float(np.linalg.norm(np.ptp(a, axis=0)) * 0.04)
    if not np.isfinite(limit) or limit <= 0 or not 0 <= min_normal <= 1:
        raise ValueError('Invalid correspondence thresholds')
    valid = (distance <= limit) & (agreement >= min_normal) & (cycle <= limit)
    return nearest, valid, {'max_distance': limit, 'min_absolute_normal_dot': min_normal,
                           'accepted_fraction': float(valid.mean()), 'cycle_distance_limit': limit}


def project_regions(source, target, regions, registration, independent, assignment, *, thresholds=None, evidence=None):
    owners = np.zeros(len(source), dtype=np.int16)
    for index, region in enumerate(regions, 1):
        owners[region["faces"]] = index
    nearest, valid, checks = correspondence_mask(source, target, registration, **(thresholds or {}))
    projected = np.where(valid, owners[nearest], 0)
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
            "face_count": len(faces), "faces": faces.tolist(), "checks": checks,
            "assignment_evidence": evidence[index-1] if evidence else None,
        })
    return result

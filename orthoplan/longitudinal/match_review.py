"""Explicit endpoint match overrides and reversible-fit evidence."""
import numpy as np
from scipy.spatial.transform import Rotation
from orthoplan.longitudinal.rigid import fit_endpoint, transform


def apply_match_overrides(source_regions, target_regions, projected, overrides):
    if overrides is None:
        return projected
    source_ids = {r['tooth'] for r in source_regions}
    targets = {r['tooth']: r for r in target_regions}
    if not isinstance(overrides, dict) or set(overrides) != source_ids:
        raise ValueError('Match review must cover every source region')
    assigned = [value for value in overrides.values() if value is not None]
    if any(value not in targets for value in assigned) or len(set(assigned)) != len(assigned):
        raise ValueError('Reviewed target regions must exist and be assigned at most once')
    result = []
    for region in source_regions:
        target_id = overrides[region['tooth']]
        if target_id is None:
            result.append(None)
            continue
        target = targets[target_id]
        result.append({**target, 'faces': target['faces'].tolist(), 'independent_label': target_id,
                       'face_count': len(target['faces']), 'match_provenance': 'user-selected-target-region'})
    return result


def reversible_fit_evidence(source, target, forward):
    """Cycle/sampling diagnostics are evidence, never calibrated uncertainty bounds."""
    pivot = source.mean(axis=0)
    reverse, _ = fit_endpoint(target, source)
    cycle = reverse @ forward
    sampled, _ = fit_endpoint(source[::2], target[::2])
    return {
        'round_trip_shift': float(np.linalg.norm(transform(pivot, cycle)-pivot)),
        'round_trip_rotation_deg': float(np.degrees(Rotation.from_matrix(cycle[:3, :3]).magnitude())),
        'sampling_shift': float(np.linalg.norm(transform(pivot, sampled)-transform(pivot, forward))),
        'sampling_rotation_deg': float(np.degrees(Rotation.from_matrix(sampled[:3, :3] @ forward[:3, :3].T).magnitude())),
        'interpretation': 'Empirical fit consistency; not calibrated measurement uncertainty',
    }

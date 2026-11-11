"""Alternative endpoint timing and sampled same-arch proximity diagnostics."""
import numpy as np
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation


def timing_profiles():
    t = np.array([i / 6 for i in range(7)])
    return {
        'uniform': {'label': 'Uniform motion', 'fractions': t.tolist()},
        'smooth': {'label': 'Slow start and finish', 'fractions': (3*t*t - 2*t*t*t).tolist()},
        'delayed': {'label': 'Delayed start', 'fractions': np.maximum(0, (t - 1/6) / (5/6)).tolist()},
    }


def posed_points(points, tooth, fraction):
    pivot = np.asarray(tooth['pivot'])
    rotation = Rotation.from_quat(tooth['quaternion_xyzw'])
    # SciPy's principal rotation vector selects the shortest quaternion arc.
    intermediate = Rotation.from_rotvec(rotation.as_rotvec() * fraction)
    return intermediate.apply(points-pivot) + pivot + np.asarray(tooth['translation']) * fraction


def proximity_distances(regions):
    result = {}
    for i, (left, points) in enumerate(regions):
        tree = cKDTree(points)
        for right, others in regions[i+1:]:
            result[(left, right)] = float(tree.query(others)[0].min())
    return result


def simulation_report(source, teeth, *, threshold=None):
    span = float(np.linalg.norm(np.ptp(source.reshape(-1, 3), axis=0)))
    threshold = span * 0.003 if threshold is None else float(threshold)
    if not np.isfinite(threshold) or threshold <= 0:
        raise ValueError('Proximity threshold must be finite and positive')
    regions = []
    for tooth in teeth:
        points = source[tooth['source_faces']].reshape(-1, 3)
        if len(points):
            indices = np.linspace(0, len(points)-1, min(256, len(points)), dtype=int)
            regions.append((tooth, points[indices]))
    baseline = proximity_distances([(t['tooth'], p) for t, p in regions])
    cache = {}
    profiles = timing_profiles()
    for profile in profiles.values():
        frames = []
        for fraction in profile['fractions']:
            if fraction not in cache:
                moved = [(t['tooth'], posed_points(p, t, fraction)) for t, p in regions]
                distances = proximity_distances(moved)
                cache[fraction] = [{'teeth': list(pair), 'sampled_distance': d,
                                    'baseline_distance': baseline[pair], 'new_proximity': baseline[pair] > threshold}
                                   for pair, d in distances.items() if d <= threshold]
            frames.append(cache[fraction])
        profile['proximity_by_week'] = frames
    return {'profiles': profiles, 'proximity_threshold': threshold,
            'units': 'source-coordinate-units', 'scope': 'within each arch only',
            'method': 'At most 256 sampled surface vertices per region; threshold is 0.3% of arch span unless supplied',
            'limitation': 'Proximity hints can miss contacts or intersections. Absence does not establish clearance. Draft boundaries can create false hints.'}

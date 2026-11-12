"""Reference selection and empirical fit sensitivity, without anatomical approval."""
import numpy as np
from scipy.spatial.transform import Rotation
from orthoplan.longitudinal.rigid import fit_endpoint, surface_points, transform, trimmed_icp


def reference_mesh(mesh, faces):
    if faces is None:
        return mesh
    indices = np.asarray(faces)
    if (indices.ndim != 1 or len(indices) < 6 or indices.dtype.kind not in 'iu'
            or np.any(indices < 0) or np.any(indices >= len(mesh))):
        raise ValueError('A reference region needs at least six valid face indices')
    return mesh[np.unique(indices)]


def register_arches(source, target, reference=None):
    reference = reference or {}
    if bool(reference.get('source_faces')) != bool(reference.get('target_faces')):
        raise ValueError('Select reference regions on both visits')
    a = surface_points(reference_mesh(target, reference.get('target_faces')), 16000)
    b = surface_points(reference_mesh(source, reference.get('source_faces')), 16000)
    matrix, metrics = fit_endpoint(a, b)
    metrics['sensitivity'] = fit_sensitivity(a, b, matrix)
    return matrix, metrics


def fit_sensitivity(source, target, best):
    """Small perturbations and alternate samples; this is not a calibrated error bound."""
    probe = source.mean(axis=0)
    trials = []
    for offset in (0, 1):
        seed = best.copy()
        perturbation = Rotation.from_euler('z', (-1 if offset else 1) * 3, degrees=True).as_matrix()
        seed[:3, :3] = perturbation @ seed[:3, :3]
        try:
            fitted, quality = trimmed_icp(source[offset::2], target[offset::2], initial=seed)
            trials.append({
                'pivot_shift': float(np.linalg.norm(transform(probe, fitted) - transform(probe, best))),
                'rotation_deg': float(np.degrees(Rotation.from_matrix(fitted[:3, :3] @ best[:3, :3].T).magnitude())),
                'p90_residual': quality['p90_residual'],
            })
        except (ValueError, np.linalg.LinAlgError):
            continue
    return {'trials': trials, 'failed_trials': 2 - len(trials),
            'max_pivot_shift': max((r['pivot_shift'] for r in trials), default=None),
            'max_rotation_deg': max((r['rotation_deg'] for r in trials), default=None),
            'interpretation': 'Sampling and initialization sensitivity, not measurement uncertainty'}

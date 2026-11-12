"""Full-triangle surface distance for one selected pair and simulated pose."""
import base64
import numpy as np
from orthoplan.surface_distance_check import surface_distance
from orthoplan.longitudinal.api import _scan
from orthoplan.longitudinal.simulation import posed_points


def contact_payload(payload, *, workspace, ui_dir):
    try:
        mesh, source = _scan(payload['scan'], workspace, ui_dir)
        preview = payload['preview']
        if preview['sources'][0] != source or preview['frame'] != 'display-oriented-bbox-centered-source-xyz':
            raise ValueError('Contact preview does not match the baseline scan')
        labels = np.frombuffer(base64.b64decode(preview['moving_face_labels_base64'], validate=True), dtype=np.uint8)
        if len(labels) != len(mesh):
            raise ValueError('Contact face labels differ from scan')
        teeth = {t['tooth']: t for t in preview['teeth']}
        ids = payload['teeth']
        fraction = float(payload['fraction'])
        if len(ids) != 2 or ids[0] == ids[1] or not 0 <= fraction <= 1:
            raise ValueError('Choose two different regions and a valid motion fraction')
        regions = []
        for key in ids:
            tooth = teeth[key]
            values = np.r_[tooth['pivot'], tooth['translation'], tooth['quaternion_xyzw']]
            if values.shape != (10,) or not np.isfinite(values).all() or abs(np.linalg.norm(values[-4:])-1) > 1e-5:
                raise ValueError('Invalid rigid tooth pose')
            faces = mesh[labels == tooth['face_label']]
            regions.append(posed_points(faces.reshape(-1, 3), tooth, fraction).reshape(-1, 3, 3))
        return {'ok': True, 'teeth': ids, 'fraction': fraction, 'units': 'source-coordinate-units',
                'result': surface_distance(*regions),
                'limitation': 'Draft region surfaces only. Surface separation does not rule out containment or establish anatomical clearance.'}
    except (ValueError, TypeError, KeyError, OSError) as exc:
        return {'ok': False, 'errors': [str(exc)]}

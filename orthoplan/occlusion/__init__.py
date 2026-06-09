"""Occlusion: bite registration + the occlusal grid that opposing-arch features share.

Advisory, on-device visualization/review geometry. Nothing here measures a bite,
asserts occlusal force, diagnoses, or claims a bite is correct or complete.
"""

from orthoplan.occlusion.grid import OcclusalGrid, build_occlusal_grid
from orthoplan.occlusion.proximity import (
    ProximityMap,
    classify_proximity,
    proximity_map_to_dict,
)
from orthoplan.occlusion.registration import (
    BiteRegistration,
    apply_registration,
    register_bite,
)

__all__ = [
    "OcclusalGrid",
    "build_occlusal_grid",
    "BiteRegistration",
    "register_bite",
    "apply_registration",
    "ProximityMap",
    "classify_proximity",
    "proximity_map_to_dict",
]

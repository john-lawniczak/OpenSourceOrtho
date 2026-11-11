"""Source-bound paired-landmark registration proposals, with held-out residuals."""

import re
import numpy as np
from orthoplan.longitudinal.rigid import rigid_fit, transform
from orthoplan.model.registration import (
    RegistrationTransform,
    RegistrationQuality,
    RegistrationMethod,
)


def landmark_proposal(packet):
    if packet.get("schema") != "ortho-landmark-pairs-v1" or packet.get("units") != "mm":
        raise ValueError("Landmark pairs must declare the millimeter contract")
    if not all(
        re.fullmatch(r"[a-f0-9]{64}", str(packet.get(key, "")))
        for key in ["source_scan_sha256", "volume_source_digest"]
    ):
        raise ValueError("Bind landmarks to source scan and volume hashes")
    source = np.asarray(packet["source_points_mm"], dtype=float)
    target = np.asarray(packet["target_points_lps_mm"], dtype=float)
    if (
        source.ndim != 2
        or source.shape[1] != 3
        or source.shape != target.shape
        or not 4 <= len(source) <= 128
        or not np.isfinite(np.r_[source, target]).all()
    ):
        raise ValueError("Provide at least four finite paired landmarks")
    matrix = rigid_fit(source, target)
    residual = np.linalg.norm(transform(source, matrix) - target, axis=1)
    leave_one_out = []
    for i in range(len(source)):
        keep = np.arange(len(source)) != i
        trial = rigid_fit(source[keep], target[keep])
        leave_one_out.append(float(np.linalg.norm(transform(source[i], trial) - target[i])))
    worst = max(leave_one_out)
    result = RegistrationTransform(
        id=packet["registration_id"],
        source_stl_asset_id=packet["source_stl_asset_id"],
        target_cbct_record_id=packet["target_cbct_record_id"],
        method=RegistrationMethod.MANUAL,
        matrix=matrix.tolist(),
        operator=packet.get("operator"),
        accepted=False,
        model_provenance="paired-landmark-rigid-fit-v1",
        quality=RegistrationQuality(
            method="paired-landmarks-with-held-out-validation",
            rmse_mm=float(np.sqrt(np.mean(np.asarray(leave_one_out) ** 2))),
            notes=[
                f"Maximum held-out landmark residual: {worst:.4f} mm",
                "Landmark residuals do not establish anatomical registration accuracy",
            ],
        ),
        notes="Review landmarks, spatial spread and held-out errors before acceptance.",
    )
    return {
        "registration": result.model_dump(mode="json"),
        "training_rmse_mm": float(np.sqrt(np.mean(residual**2))),
        "residuals_mm": residual.tolist(),
        "leave_one_out_mm": leave_one_out,
        "max_held_out_mm": worst,
        "requires_review": True,
        "source_scan_sha256": packet.get("source_scan_sha256"),
        "volume_source_digest": packet.get("volume_source_digest"),
    }

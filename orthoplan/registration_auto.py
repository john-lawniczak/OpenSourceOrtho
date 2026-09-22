"""Optional automatic STL-to-CBCT registration experiment (Open3D ICP).

This is an EXPERIMENT, gated behind the optional ``mesh-processing`` extra
(Open3D). It proposes a ``RegistrationTransform`` from two point sets via ICP and
attaches quality metrics, but always returns it with ``accepted=False``: a human
must review the quality and accept it before any CBCT-derived check runs. When
Open3D is not installed, it fails closed (returns an error) rather than guessing.
"""

from __future__ import annotations

from dataclasses import dataclass

from orthoplan.model.registration import (
    RegistrationMethod,
    RegistrationQuality,
    RegistrationTransform,
)

Point = tuple[float, float, float]


class RegistrationBackendUnavailable(RuntimeError):
    """Raised when automatic registration is requested but Open3D is missing."""


@dataclass(frozen=True)
class RegistrationProposal:
    """Review packet for an automatic STL-to-CBCT registration proposal."""

    transform: RegistrationTransform
    status: str
    requires_human_acceptance: bool = True
    caveat: str = (
        "Automatic registration is a geometric proposal only. It is not trusted "
        "until a human reviews quality metrics and explicitly accepts it."
    )


def open3d_available() -> bool:
    try:
        import open3d  # noqa: F401
    except ImportError:
        return False
    return True


def propose_auto_registration(
    source_points: list[Point],
    target_points: list[Point],
    *,
    registration_id: str,
    source_stl_asset_id: str,
    target_cbct_record_id: str,
    max_correspondence_mm: float = 1.0,
) -> RegistrationProposal:
    """Create an unaccepted automatic-registration review proposal."""

    transform = auto_register_icp(
        source_points,
        target_points,
        registration_id=registration_id,
        source_stl_asset_id=source_stl_asset_id,
        target_cbct_record_id=target_cbct_record_id,
        max_correspondence_mm=max_correspondence_mm,
    )
    notes = list(transform.quality.notes if transform.quality else [])
    notes.append("review metrics before setting accepted=True")
    if transform.quality is not None:
        transform = transform.model_copy(
            update={"quality": transform.quality.model_copy(update={"notes": notes})}
        )
    return RegistrationProposal(transform=transform, status="proposed")


def auto_register_icp(
    source_points: list[Point],
    target_points: list[Point],
    *,
    registration_id: str,
    source_stl_asset_id: str,
    target_cbct_record_id: str,
    max_correspondence_mm: float = 1.0,
) -> RegistrationTransform:
    """Propose an ICP registration. Returns an UNACCEPTED transform for review."""

    try:
        import numpy as np
        import open3d as o3d
    except ImportError as exc:  # pragma: no cover - depends on optional extra
        raise RegistrationBackendUnavailable(
            "automatic registration requires the optional 'mesh-processing' extra (Open3D)"
        ) from exc
    if not source_points or not target_points:
        raise ValueError("source and target point sets must be non-empty")

    source = o3d.geometry.PointCloud()
    source.points = o3d.utility.Vector3dVector(np.asarray(source_points, dtype=float))
    target = o3d.geometry.PointCloud()
    target.points = o3d.utility.Vector3dVector(np.asarray(target_points, dtype=float))

    result = o3d.pipelines.registration.registration_icp(
        source,
        target,
        max_correspondence_mm,
        np.eye(4),
        o3d.pipelines.registration.TransformationEstimationPointToPoint(),
    )
    matrix = [[float(v) for v in row] for row in result.transformation]
    quality = RegistrationQuality(
        method="open3d-icp",
        rmse_mm=float(result.inlier_rmse),
        inlier_ratio=float(result.fitness),
        fitness=float(result.fitness),
        notes=["automatic ICP proposal - requires human acceptance"],
    )
    return RegistrationTransform(
        id=registration_id,
        source_stl_asset_id=source_stl_asset_id,
        target_cbct_record_id=target_cbct_record_id,
        method=RegistrationMethod.AUTOMATIC_ICP,
        matrix=matrix,
        model_provenance="open3d-icp",
        quality=quality,
        accepted=False,
    )

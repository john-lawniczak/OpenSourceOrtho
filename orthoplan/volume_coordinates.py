"""Validate voxel-to-patient transforms and derive orientation-independent draft axes."""

import math


def validate_voxel_affine(matrix):
    if (
        not isinstance(matrix, (list, tuple))
        or len(matrix) != 4
        or any(not isinstance(row, (list, tuple)) or len(row) != 4 for row in matrix)
        or not all(isinstance(v, (int, float)) and math.isfinite(v) for row in matrix for v in row)
        or list(matrix[3]) != [0, 0, 0, 1]
    ):
        raise ValueError("Invalid voxel-to-patient affine")
    columns = [tuple(matrix[i][j] for i in range(3)) for j in range(3)]
    lengths = [math.sqrt(sum(v * v for v in column)) for column in columns]
    if min(lengths) <= 0:
        raise ValueError("Voxel affine must be invertible")
    for i in range(3):
        for j in range(i):
            if (
                abs(sum(columns[i][k] * columns[j][k] for k in range(3)))
                > lengths[i] * lengths[j] * 1e-5
            ):
                raise ValueError("Sheared voxel axes require resampling")


def patient_point(voxel, spacing, affine=None):
    if affine is None:
        return tuple(float(voxel[i]) * spacing[i] for i in range(3))
    return tuple(sum(affine[i][j] * voxel[j] for j in range(3)) + affine[i][3] for i in range(3))


def validate_volume_mask(payload):
    spacing = payload.voxel_spacing_mm
    if len(spacing) != 3 or not all(math.isfinite(v) and v > 0 for v in spacing):
        raise ValueError("Voxel spacing must be finite and positive")
    matrix = payload.voxel_to_patient_mm
    if matrix is not None:
        validate_voxel_affine(matrix)
        if any(
            abs(sum(matrix[i][j] ** 2 for i in range(3)) - spacing[j] ** 2) > spacing[j] ** 2 * 1e-5
            for j in range(3)
        ):
            raise ValueError("Voxel affine and spacing disagree")
    dims = payload.volume_dimensions
    if dims is not None and (len(dims) != 3 or any(v <= 0 for v in dims)):
        raise ValueError("Volume dimensions must be positive")
    for region in [*payload.root_voxels_by_tooth.values(), payload.bone_voxels]:
        if any(
            len(p) != 3
            or any(v < 0 or (dims is not None and v >= dims[i]) for i, v in enumerate(p))
            for p in region
        ):
            raise ValueError("Mask voxel is outside the volume")


def preserve_mask_provenance(proposal, mask):
    """Keep source binding and ROI truncation evidence through draft conversion."""
    boundaries = set(mask.get("roi_boundary_regions", []))
    for obj in proposal.all_objects():
        label = obj.tooth.value if hasattr(obj, "tooth") else "bone"
        if mask.get("source_digest"):
            obj.notes.append(f"Volume source digest: {mask['source_digest']}")
        if label in boundaries:
            obj.out_of_field = True
            obj.notes.append("Mask reaches its selected ROI boundary; anatomy may be truncated")
            obj.quality_metrics["touches_roi_boundary"] = True


def patient_centerline(points):
    center = tuple(sum(p[i] for p in points) / len(points) for i in range(3))
    offsets = [tuple(p[i] - center[i] for i in range(3)) for p in points]
    covariance = [[sum(p[i] * p[j] for p in offsets) for j in range(3)] for i in range(3)]
    axis = max(range(3), key=lambda i: covariance[i][i])
    direction = [float(i == axis) for i in range(3)]
    for _ in range(32):
        vector = [sum(covariance[i][j] * direction[j] for j in range(3)) for i in range(3)]
        length = math.sqrt(sum(v * v for v in vector))
        if length < 1e-12:
            return [center]
        direction = [v / length for v in vector]
    projection = [sum(p[i] * direction[i] for i in range(3)) for p in offsets]
    lo, hi = min(projection), max(projection)
    bins = min(32, max(2, round(len(points) ** (1 / 3)) * 2))
    groups = {}
    for point, position in zip(points, projection):
        index = min(bins - 1, int((position - lo) / max(hi - lo, 1e-12) * bins))
        groups.setdefault(index, []).append(point)
    return [
        tuple(sum(p[i] for p in group) / len(group) for i in range(3))
        for _, group in sorted(groups.items())
    ]

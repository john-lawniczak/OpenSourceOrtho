"""Stream a regular DICOM slice series into a local, geometry-correct review packet."""

import base64
import hashlib
from pathlib import Path
import numpy as np

TAGS = [
    "SeriesInstanceUID",
    "Rows",
    "Columns",
    "PixelSpacing",
    "ImagePositionPatient",
    "ImageOrientationPatient",
    "NumberOfFrames",
]


def discover_series(directory):
    import pydicom

    groups = {}
    for path in sorted(Path(directory).rglob("*")):
        if not path.is_file():
            continue
        try:
            ds = pydicom.dcmread(path, stop_before_pixels=True, specific_tags=TAGS)
        except (pydicom.errors.InvalidDicomError, OSError):
            continue
        if (
            any(not hasattr(ds, tag) for tag in TAGS[:-1])
            or int(getattr(ds, "NumberOfFrames", 1)) != 1
        ):
            continue
        groups.setdefault(str(ds.SeriesInstanceUID), []).append((path, ds))
    candidates = sorted(groups.values(), key=len, reverse=True)
    if not candidates or len(candidates[0]) < 2:
        raise ValueError("No multi-slice regular DICOM series found")
    if len(candidates) > 1 and len(candidates[0]) == len(candidates[1]):
        raise ValueError("Ambiguous largest series; select a folder containing one series")
    return candidates[0], len(candidates) - 1


def series_geometry(records, stride):
    first = records[0][1]
    orientation = np.asarray(first.ImageOrientationPatient, dtype=float)
    row, column = orientation[:3], orientation[3:]
    spacing = np.asarray(first.PixelSpacing, dtype=float)
    if (
        orientation.shape != (6,)
        or spacing.shape != (2,)
        or not np.isfinite(np.r_[orientation, spacing]).all()
        or np.any(spacing <= 0)
        or not np.allclose(
            [np.linalg.norm(row), np.linalg.norm(column), np.dot(row, column)], [1, 1, 0], atol=1e-5
        )
    ):
        raise ValueError("Invalid DICOM direction cosines or pixel spacing")
    normal = np.cross(row, column)
    ordered = sorted(
        records, key=lambda record: float(np.dot(record[1].ImagePositionPatient, normal))
    )
    positions = np.array([record[1].ImagePositionPatient for record in ordered], dtype=float)
    distances = positions @ normal
    step = float(np.median(np.diff(distances)))
    if (
        not np.isfinite(positions).all()
        or step <= 0
        or not np.allclose(np.diff(distances), step, atol=1e-3)
    ):
        raise ValueError("Duplicate, irregular, or missing slice positions")
    expected = positions[0] + np.arange(len(positions))[:, None] * step * normal
    if not np.allclose(positions, expected, atol=1e-3):
        raise ValueError("Sheared/tilted slice stacks need resampling before review")
    for _, ds in ordered:
        if (
            ds.Rows != first.Rows
            or ds.Columns != first.Columns
            or not np.allclose(ds.PixelSpacing, spacing, atol=1e-6)
            or not np.allclose(ds.ImageOrientationPatient, orientation, atol=1e-6)
        ):
            raise ValueError("Series dimensions, orientation, or spacing changed between slices")
    affine = np.eye(4)
    affine[:3, :3] = np.column_stack(
        [row * spacing[1] * stride, column * spacing[0] * stride, normal * step * stride]
    )
    affine[:3, 3] = positions[0]
    return ordered, affine


def build_review_packet(directory, *, stride=4, max_voxels=20_000_000):
    import pydicom

    if type(stride) is not int or not 1 <= stride <= 32:
        raise ValueError("Choose an integer downsampling stride from 1 to 32")
    records, excluded = discover_series(directory)
    ordered, affine = series_geometry(records, stride)
    first = ordered[0][1]
    shape = (
        (len(ordered) + stride - 1) // stride,
        (int(first.Rows) + stride - 1) // stride,
        (int(first.Columns) + stride - 1) // stride,
    )
    if np.prod(shape) > max_voxels:
        raise ValueError(
            "Review packet exceeds voxel budget; increase stride or crop the source series"
        )
    volume = np.empty(shape, dtype="<f4")
    digest = hashlib.sha256()
    for i, (path, _) in enumerate(ordered):
        digest.update(hashlib.sha256(path.read_bytes()).digest())
        if i % stride:
            continue
        ds = pydicom.dcmread(path)
        pixels = ds.pixel_array.astype(np.float32) * float(getattr(ds, "RescaleSlope", 1)) + float(
            getattr(ds, "RescaleIntercept", 0)
        )
        if pixels.shape != (int(first.Rows), int(first.Columns)) or not np.isfinite(pixels).all():
            raise ValueError("Invalid decoded slice pixels")
        volume[i // stride] = pixels[::stride, ::stride]
    raw = volume.tobytes()
    return {
        "schema": "ortho-volume-review-v1",
        "frame": "dicom-patient-lps-mm",
        "dtype": "float32-le",
        "dimensions_xyz": list(reversed(shape)),
        "voxel_to_patient_mm": affine.tolist(),
        "voxel_spacing_mm": np.linalg.norm(affine[:3, :3], axis=0).tolist(),
        "source_digest": digest.hexdigest(),
        "pixel_sha256": hashlib.sha256(raw).hexdigest(),
        "source_slices": len(ordered),
        "excluded_series": excluded,
        "stride": stride,
        "intensity_range": [float(volume.min()), float(volume.max())],
        "pixels_base64": base64.b64encode(raw).decode("ascii"),
        "status": "unreviewed-local-volume",
        "limitation": "Downsampled review pixels; intensity thresholds are not tissue identity or reviewed anatomy.",
    }

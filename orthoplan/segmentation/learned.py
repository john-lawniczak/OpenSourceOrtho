"""Optional local ONNX tooth segmenter behind the ToothSegment contract.

No model is committed. The backend is inert unless the optional ``ml-seg`` extra
and user-supplied weights are present; otherwise callers fall back to the
heuristic. Outputs are advisory proposals for human review, never diagnosis,
treatment clearance, or physical-use approval.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

from orthoplan.model.assets import ArchName
from orthoplan.model.geometry import Vec3
from orthoplan.segmentation.heuristic import (
    Triangle,
    ToothSegment,
    default_arch_order,
)

_WEIGHTS_ENV = "OPENSOURCE_ORTHO_SEG_WEIGHTS"
_ARCH_WEIGHT_FILE: dict[ArchName, str] = {
    "maxillary": "maxillary.onnx",
    "mandibular": "mandibular.onnx",
}
_FEATURE_DIM = 15
_GINGIVA_CLASS = 0
_DEFAULT_CONFIDENCE = 0.5
_DEFAULT_MIN_LABEL_RUN = 2

FaceLabelRunner = Callable[[list[Vec3], ArchName, Path], list[int]]


class SegmenterUnavailable(RuntimeError):
    """The learned backend cannot run, so callers should use the fallback."""


def _onnxruntime_available() -> bool:
    """True when the optional ``onnxruntime`` runtime is importable (lazy)."""

    try:
        import onnxruntime  # noqa: F401
    except ImportError:
        return False
    return True


def resolve_weights_by_arch(weights: str | Path | None = None) -> dict[ArchName, Path]:
    """Resolve user-supplied ONNX weights to a per-arch path map, or raise.

    ``weights`` (or the ``OPENSOURCE_ORTHO_SEG_WEIGHTS`` env var) is either a
    directory containing ``maxillary.onnx`` + ``mandibular.onnx`` or a single
    ``.onnx`` file used for both arches. Raises :class:`SegmenterUnavailable` when
    nothing is configured or the files are absent, so the loader falls back cleanly.
    """

    raw = weights if weights is not None else os.environ.get(_WEIGHTS_ENV)
    if not raw:
        raise SegmenterUnavailable(
            f"no learned-segmenter weights configured (set ${_WEIGHTS_ENV} to an "
            ".onnx file or a directory of per-arch weights)"
        )
    path = Path(raw).expanduser()
    if path.is_file():
        return {arch: path for arch in _ARCH_WEIGHT_FILE}
    if path.is_dir():
        resolved = {arch: path / name for arch, name in _ARCH_WEIGHT_FILE.items()}
        missing = [str(p) for p in resolved.values() if not p.is_file()]
        if missing:
            raise SegmenterUnavailable(
                f"learned-segmenter weights directory {path} is missing: {missing}"
            )
        return resolved
    raise SegmenterUnavailable(f"learned-segmenter weights path does not exist: {path}")


def load_learned_segmenter(
    weights: str | Path | None = None, *, runner: FaceLabelRunner | None = None
) -> LearnedMeshSegmenter:
    """Build the learned segmenter if the extra is installed AND weights resolve.

    Raises :class:`SegmenterUnavailable` otherwise - the signal the loader catches
    to keep the heuristic as the default backend.
    """

    weights_by_arch = resolve_weights_by_arch(weights)
    if runner is None and not _onnxruntime_available():
        raise SegmenterUnavailable(
            "onnxruntime is not installed (pip install 'opensource-ortho[ml-seg]')"
        )
    return LearnedMeshSegmenter(weights_by_arch, runner=runner)


def _facets(vertices: list[Vec3]) -> list[Triangle]:
    return [
        (vertices[i], vertices[i + 1], vertices[i + 2])
        for i in range(0, len(vertices) - 2, 3)
    ]


def _tri_centroid(tri: Triangle) -> Vec3:
    return (
        (tri[0][0] + tri[1][0] + tri[2][0]) / 3.0,
        (tri[0][1] + tri[1][1] + tri[2][1]) / 3.0,
        (tri[0][2] + tri[1][2] + tri[2][2]) / 3.0,
    )


def _mean3(points: list[Vec3]) -> Vec3:
    count = len(points)
    return (
        sum(p[0] for p in points) / count,
        sum(p[1] for p in points) / count,
        sum(p[2] for p in points) / count,
    )


def _face_normal(tri: Triangle) -> Vec3:
    ax, ay, az = (tri[1][i] - tri[0][i] for i in range(3))
    bx, by, bz = (tri[2][i] - tri[0][i] for i in range(3))
    nx, ny, nz = (ay * bz - az * by, az * bx - ax * bz, ax * by - ay * bx)
    length = (nx * nx + ny * ny + nz * nz) ** 0.5
    if length == 0:
        return (0.0, 0.0, 0.0)
    return (nx / length, ny / length, nz / length)


def build_cell_features(facets: list[Triangle], centroids: list[Vec3]) -> list[list[float]]:
    """Per-cell feature rows (pure Python) for the exported model's input tensor.

    Each row is the documented 15-dim vector: 9 raw vertex coordinates, the 3-dim
    face normal, and the centroid's position relative to the mesh centroid. The
    default ONNX runner converts these to a numpy array; keeping the math in pure
    Python lets it be unit-tested without numpy or a model.
    """

    if not centroids:
        return []
    mesh_center = _mean3(centroids)
    rows: list[list[float]] = []
    for tri, centroid in zip(facets, centroids):
        normal = _face_normal(tri)
        relative = tuple(centroid[i] - mesh_center[i] for i in range(3))
        rows.append([*tri[0], *tri[1], *tri[2], *normal, *relative])
    return rows


def segments_from_labels(
    facets: list[Triangle],
    centroids: list[Vec3],
    labels: list[int],
    *,
    arch: ArchName,
    tooth_values: tuple[str, ...] | None = None,
    confidence_by_label: dict[int, float] | None = None,
) -> list[ToothSegment]:
    """Group per-face class labels into anatomically ordered ToothSegments.

    Class ``0`` is gingiva (discarded); classes ``1..N`` map onto FDI order
    ``tooth_values`` (or the canonical arch order), so the labelling matches the
    heuristic and honours the user's missing-teeth anchoring. Out-of-range labels
    are dropped defensively.
    """

    order = tooth_values if tooth_values is not None else default_arch_order(arch)
    groups: dict[int, list[int]] = {}
    for index, label in enumerate(labels):
        if label == _GINGIVA_CLASS or not 1 <= label <= len(order):
            continue
        groups.setdefault(label, []).append(index)

    segments: list[ToothSegment] = []
    for label in sorted(groups):
        indices = groups[label]
        confidence = (confidence_by_label or {}).get(label, _DEFAULT_CONFIDENCE)
        segments.append(
            ToothSegment(
                tooth_value=order[label - 1],
                triangles=[facets[i] for i in indices],
                centroid=_mean3([centroids[i] for i in indices]),
                confidence=round(min(1.0, max(0.0, confidence)), 3),
            )
        )
    return segments


def repair_short_label_runs(labels: list[int], *, min_run: int = _DEFAULT_MIN_LABEL_RUN) -> list[int]:
    """Replace short non-gingiva label islands with the surrounding label.

    ONNX mesh classifiers emit one label per face. On crowded/contacting arches,
    isolated one-face flips near interproximal contacts add manual cleanup without
    changing the broad tooth boundary. This conservative repair only touches a
    short run when the same non-gingiva label appears on both sides.
    """

    if min_run <= 1 or len(labels) < 3:
        return labels
    repaired = list(labels)
    start = 0
    while start < len(labels):
        label = labels[start]
        end = start + 1
        while end < len(labels) and labels[end] == label:
            end += 1
        if 0 < start and end < len(labels) and 0 < (end - start) < min_run:
            left = labels[start - 1]
            right = labels[end]
            if left == right and left != _GINGIVA_CLASS and label != left:
                repaired[start:end] = [left] * (end - start)
        start = end
    return repaired


def _onnx_face_labels(vertices: list[Vec3], arch: ArchName, weights_path: Path) -> list[int]:
    """Run a hash-bound explicit model contract; never guess tensor layout."""
    from orthoplan.segmentation.model_contract import run_contract
    order = default_arch_order(arch)
    labels = run_contract(vertices, arch, weights_path)
    return [order.index(str(value))+1 if str(value) in order else 0 for value in labels]


class LearnedMeshSegmenter:
    """On-device ONNX tooth segmenter exposing the standard segmenter contract."""

    name = "learned-mesh-onnx"
    version = "0.1.0"
    backend = "onnxruntime"

    def __init__(
        self,
        weights_by_arch: dict[ArchName, Path],
        *,
        runner: FaceLabelRunner | None = None,
        min_label_run: int = _DEFAULT_MIN_LABEL_RUN,
    ) -> None:
        self._weights_by_arch = weights_by_arch
        self._runner = runner or _onnx_face_labels
        self._min_label_run = min_label_run
        self._injected_runner = runner is not None

    def segment(
        self,
        vertices: list[Vec3],
        *,
        arch: ArchName,
        tooth_values: tuple[str, ...] | None = None,
    ) -> list[ToothSegment]:
        weights_path = self._weights_by_arch.get(arch)
        if weights_path is None:
            raise SegmenterUnavailable(f"no learned weights for arch {arch!r}")
        facets = _facets(vertices)
        if not facets:
            return []
        centroids = [_tri_centroid(tri) for tri in facets]
        labels = self._runner(vertices, arch, weights_path)
        if len(labels) != len(facets) or any(type(v) is not int or not 0 <= v <= len(default_arch_order(arch)) for v in labels):
            raise SegmenterUnavailable("Model returned invalid face labels")
        # STL face ordering has no anatomical meaning. Repair only shared-edge neighbors.
        if self._min_label_run > 1:
            try:
                from orthoplan.segmentation.topology import repair_face_islands
                labels = repair_face_islands(facets, labels)
            except ImportError:
                pass
        if not self._injected_runner and tooth_values is not None:
            full_order = default_arch_order(arch)
            labels = [tooth_values.index(full_order[v-1])+1 if v and full_order[v-1] in tooth_values else 0 for v in labels]
        return segments_from_labels(
            facets, centroids, labels, arch=arch, tooth_values=tooth_values
        )

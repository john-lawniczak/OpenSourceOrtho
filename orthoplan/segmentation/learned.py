"""Optional learned (ONNX) tooth segmenter, behind the same ToothSegment contract.

This is the on-device learned backend the heuristic was always a fallback for. It
drops into ``load_local_segmenter`` (``segmentation/auto.py``) WITHOUT changing any
caller: it returns the same :class:`ToothSegment` proposals as the heuristic, so
``segmentation_api``, ``mesh_export``, ``api.render_meshes``, and the viewer are
untouched.

Phase 1 ships the CONTRACT, not a model. There is no committed model and no torch
at runtime (see docs/segmentation-learned-backend.md). The backend is therefore
designed to be *inert by default*:

- It needs the optional ``ml-seg`` extra (``onnxruntime`` + ``numpy``); neither is
  imported at module load, so importing this file is always safe in the light core.
- It needs user-supplied weights resolved from a path / env var; weights are never
  committed (size + provenance/licensing - see the doc's "Model availability").
- When onnxruntime OR weights are missing, the factory raises
  :class:`SegmenterUnavailable`, which ``load_local_segmenter`` catches to fall
  back to the always-on heuristic. The chosen backend name is surfaced in
  ``_segmenter_metadata`` either way.

On-device only: like the heuristic, inference runs locally. Scan bytes (PHI) never
leave the machine - there is no hosted-model path here.

Everything this produces is an advisory PROPOSAL for human review: never a
diagnosis, a treatment decision, or a claim that care is needed, possible, safe, or
complete.
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

# User-supplied weights location: a directory holding ``maxillary.onnx`` and
# ``mandibular.onnx``, or a single ``.onnx`` file used for both arches. Resolved at
# runtime so the project never commits or redistributes weights.
_WEIGHTS_ENV = "OPENSOURCE_ORTHO_SEG_WEIGHTS"
_ARCH_WEIGHT_FILE: dict[ArchName, str] = {
    "maxillary": "maxillary.onnx",
    "mandibular": "mandibular.onnx",
}
# Per-cell feature width the exported model is expected to consume: 9 vertex coords
# + 3 face normal + 3 relative position (see docs - MeshSegNet-style preprocessing).
_FEATURE_DIM = 15
# Class convention the exported model MUST emit: 0 = gingiva (discarded), 1..N =
# teeth in canonical FDI arch order. The export spike maps the model's raw classes
# onto this so labelling stays consistent with the heuristic.
_GINGIVA_CLASS = 0
# Placeholder per-tooth confidence until a real model supplies softmax probabilities.
# Like the heuristic, confidence stays below 1.0: this is a draft, not a measurement.
_DEFAULT_CONFIDENCE = 0.5

# A runner maps (vertices, arch, weights_path) -> one integer class label per face.
# Injectable so the contract logic (label -> ToothSegment) is testable without
# onnxruntime or weights; the default runner does the numpy + ONNX work.
FaceLabelRunner = Callable[[list[Vec3], ArchName, Path], list[int]]


class SegmenterUnavailable(RuntimeError):
    """The learned backend cannot run (no onnxruntime, or no resolvable weights).

    This is the explicit "inert" signal Phase 1 requires: ``load_local_segmenter``
    catches it and falls back to the heuristic, so the core never depends on the
    optional ``ml-seg`` extra.
    """


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

    if runner is None and not _onnxruntime_available():
        raise SegmenterUnavailable(
            "onnxruntime is not installed (pip install 'opensource-ortho[ml-seg]')"
        )
    weights_by_arch = resolve_weights_by_arch(weights)
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


def _onnx_face_labels(vertices: list[Vec3], arch: ArchName, weights_path: Path) -> list[int]:
    """Default runner: build features, run the ONNX session, return per-face labels.

    Imports numpy and onnxruntime lazily (the ``ml-seg`` extra). The session I/O is
    intentionally generic - it feeds the first input and argmaxes per-cell logits -
    because the exact tensor names/shapes are pinned by the export spike, not here.
    """

    import numpy as np  # noqa: PLC0415 - optional extra, imported on use only
    import onnxruntime as ort  # noqa: PLC0415

    facets = _facets(vertices)
    centroids = [_tri_centroid(tri) for tri in facets]
    features = np.asarray(build_cell_features(facets, centroids), dtype=np.float32)
    session = ort.InferenceSession(str(weights_path), providers=["CPUExecutionProvider"])
    raw = session.run(None, {session.get_inputs()[0].name: features[np.newaxis, ...]})[0]
    logits = np.squeeze(raw)
    labels = logits.argmax(axis=-1) if logits.ndim > 1 else logits
    return [int(value) for value in np.asarray(labels).reshape(-1)]


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
    ) -> None:
        self._weights_by_arch = weights_by_arch
        self._runner = runner or _onnx_face_labels

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
        return segments_from_labels(
            facets, centroids, labels, arch=arch, tooth_values=tooth_values
        )

"""Local segmentation-model abstraction and the advisory proposal it produces.

``load_local_segmenter()`` returns the segmenter used by ``POST /api/segment``.
Today it is a local hybrid geometric segmenter with a dependency-free baseline
and optional Open3D mesh-processing support. This module is still the seam where
an on-device learned model (e.g. a Teeth3DS / MeshSegNet network) can be dropped
in WITHOUT changing callers, by implementing
:class:`SegmentationModel`. Such a model MUST run locally: intraoral scans are
PHI, so segmentation never calls a hosted API.

Every result is advisory and untrusted: it is a reviewable PROPOSAL, never an
auto-accepted result, and it never asserts a plan is needed, possible, or done.
"""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, Field

from orthoplan.evaluation.finding import (
    Finding,
    FindingCategory,
    FindingProvenance,
    FindingSeverity,
    quarantine_findings,
)
from orthoplan.model.assets import ArchName
from orthoplan.model.geometry import Vec3
from orthoplan.segmentation.heuristic import (
    ToothSegment,
    auto_segment_arch,
    default_arch_order,
)
from orthoplan.segmentation.hybrid import (
    CrossModalReport,
    hybrid_segment_arch_with_diagnostics,
    mesh_processing_backend,
)

SEGMENTATION_CAVEAT = (
    "Automated segmentation is a draft produced by a model, not a measurement. "
    "Each tooth region and its number must be reviewed and corrected before use. "
    "It is educational only: it does not diagnose, does not indicate whether "
    "treatment is needed or possible, and never means a plan is finished."
)


class SegmentationModel(Protocol):
    """A local, on-device tooth segmenter. Implementations must not call the network."""

    name: str
    version: str

    def segment(
        self,
        vertices: list[Vec3],
        *,
        arch: ArchName,
        tooth_values: tuple[str, ...] | None = None,
    ) -> list[ToothSegment]:
        ...


class HeuristicArchSegmenter:
    """Dependency-free baseline segmenter (valley-based arch heuristic)."""

    name = "heuristic-arch-valley"
    version = "0.2.0"

    def segment(
        self,
        vertices: list[Vec3],
        *,
        arch: ArchName,
        tooth_values: tuple[str, ...] | None = None,
    ) -> list[ToothSegment]:
        return auto_segment_arch(vertices, arch=arch, tooth_values=tooth_values)


class HybridArchSegmenter:
    """Local hybrid segmenter using arch position, height, normals, and curvature."""

    name = "hybrid-arch-graph-cut"
    version = "0.2.0"
    # The hybrid segmenter can bias cut placement with CBCT boundary priors and
    # report cross-modal agreement (see segment_with_priors). Other backends
    # (learned, heuristic) ignore priors; callers must check this flag.
    supports_boundary_priors = True

    def segment(
        self,
        vertices: list[Vec3],
        *,
        arch: ArchName,
        tooth_values: tuple[str, ...] | None = None,
    ) -> list[ToothSegment]:
        segments, _report = self.segment_with_priors(
            vertices, arch=arch, tooth_values=tooth_values
        )
        return segments

    def segment_with_priors(
        self,
        vertices: list[Vec3],
        *,
        arch: ArchName,
        tooth_values: tuple[str, ...] | None = None,
        prior_points: list[Vec3] | None = None,
        prior_boost: bool = False,
    ) -> tuple[list[ToothSegment], CrossModalReport | None]:
        """Segment with optional CBCT boundary priors + cross-modal agreement report."""

        segments, diagnostics = hybrid_segment_arch_with_diagnostics(
            vertices,
            arch=arch,
            tooth_values=tooth_values,
            prior_points=prior_points,
            prior_boost=prior_boost,
        )
        if segments:
            return segments, diagnostics.cross_modal
        return auto_segment_arch(vertices, arch=arch, tooth_values=tooth_values), None

    @property
    def backend(self) -> str:
        return mesh_processing_backend()


def tooth_values_for_arch(
    arch: ArchName, missing_teeth: list[str] | None
) -> tuple[str, ...] | None:
    """Explicit FDI labels for an arch with the user-marked teeth removed.

    Geometry cannot tell WHICH tooth is absent, so the user marks the gap(s). With
    that signal the detected regions are labelled by the canonical order minus the
    marked teeth - turning a positional mislabel into a correct one. Returns
    ``None`` when nothing relevant is marked, so the segmenter falls back to
    detecting the count itself.
    """

    if not missing_teeth:
        return None
    order = default_arch_order(arch)
    marked = {str(tooth).strip() for tooth in missing_teeth} & set(order)
    if not marked:
        return None
    return tuple(tooth for tooth in order if tooth not in marked)


def _maybe_learned_segmenter() -> SegmentationModel | None:
    """Return the optional learned ONNX segmenter, or ``None`` to use the fallback.

    The learned backend is an optional extra with user-supplied, never-committed
    weights. Any "unavailable" signal (extra not installed, no weights) is swallowed
    here so the heuristic stays the always-on default and the core never depends on
    the extra. A broken optional backend must likewise never take down segmentation.
    """

    try:
        from orthoplan.segmentation.learned import (
            SegmenterUnavailable,
            load_learned_segmenter,
        )
    except ImportError:
        return None
    try:
        return load_learned_segmenter()
    except SegmenterUnavailable:
        return None
    except Exception:  # noqa: BLE001 - the optional backend must never break the core
        return None


def load_local_segmenter() -> SegmentationModel:
    """Return the active on-device segmenter.

    Prefers the optional learned ONNX backend when the ``ml-seg`` extra is installed
    AND user-supplied weights resolve; otherwise falls back to the dependency-free
    hybrid heuristic. Either backend runs locally (scans are PHI), exposes
    ``name``/``version``, and returns :class:`ToothSegment` objects, so the API, mesh
    export, and UI are unaffected. The active backend's name surfaces in
    ``_segmenter_metadata`` / ``segment_payload``.
    """

    return _maybe_learned_segmenter() or HybridArchSegmenter()


class ProposedTooth(BaseModel):
    """One reviewable per-tooth row in a segmentation proposal."""

    arch: ArchName
    tooth: str
    confidence: float = Field(ge=0.0, le=1.0)
    mesh_asset_id: str
    url: str
    centroid: Vec3
    vertex_count: int = Field(ge=0)


def build_advisory_findings(overall_confidence: float) -> list[Finding]:
    """Linted, model-provenance advisory findings for a segmentation proposal."""

    candidates = [
        Finding(
            severity=FindingSeverity.INFO,
            category=FindingCategory.EDUCATION,
            provenance=FindingProvenance.MODEL,
            title="Automated segmentation is a draft",
            message=(
                "These per-tooth regions were proposed by a model and are not "
                "measured or verified. Review and correct each tooth before using "
                "them in a plan."
            ),
        ),
        Finding(
            severity=FindingSeverity.INFO,
            category=FindingCategory.EDUCATION,
            provenance=FindingProvenance.MODEL,
            title="Confidence is separation, not certainty",
            message=(
                f"Overall draft confidence is {overall_confidence:.2f}. Per-tooth "
                "confidence reflects only how cleanly a region separated from its "
                "neighbours; it says nothing about tooth identity or treatment."
            ),
        ),
    ]
    accepted, _rejected = quarantine_findings(candidates)
    return accepted


def build_count_advisories(count_by_arch: dict[ArchName, int]) -> list[Finding]:
    """Advisory findings when a scan's detected crown count is not a full arch.

    The segmenter derives the tooth count from the scan instead of assuming a full
    arch, so a different count is expected and informative - but it also means the
    FDI numbers are a positional guess (we cannot tell WHICH tooth is absent from
    crown geometry), so the user is told to review the numbers.
    """

    candidates: list[Finding] = []
    for arch, observed in sorted(count_by_arch.items()):
        expected = len(default_arch_order(arch))
        if not observed or observed == expected:
            continue
        candidates.append(
            Finding(
                severity=FindingSeverity.INFO,
                category=FindingCategory.EDUCATION,
                provenance=FindingProvenance.MODEL,
                title="Detected tooth count differs from a full arch",
                message=(
                    f"This {arch} scan segmented into {observed} crowns, not the usual "
                    f"{expected}. Tooth numbers are assigned by position, so review "
                    "them - especially around any missing or extra tooth."
                ),
            )
        )
    accepted, _rejected = quarantine_findings(candidates)
    return accepted

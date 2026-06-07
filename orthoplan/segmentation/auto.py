"""Local segmentation-model abstraction and the advisory proposal it produces.

``load_local_segmenter()`` returns the segmenter used by ``POST /api/segment``.
Today it is the dependency-free heuristic (``segmentation/heuristic.py``). This
module is the seam where an on-device learned model (e.g. a Teeth3DS / MeshSegNet
network) can be dropped in WITHOUT changing callers, by implementing
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
from orthoplan.segmentation.heuristic import ToothSegment, auto_segment_arch

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

    def segment(self, vertices: list[Vec3], *, arch: ArchName) -> list[ToothSegment]:
        ...


class HeuristicArchSegmenter:
    """Dependency-free baseline segmenter (arch-sector heuristic)."""

    name = "heuristic-arch-sector"
    version = "0.1.0"

    def segment(self, vertices: list[Vec3], *, arch: ArchName) -> list[ToothSegment]:
        return auto_segment_arch(vertices, arch=arch)


def load_local_segmenter() -> SegmentationModel:
    """Return the active on-device segmenter.

    Swap point for a real learned model: return e.g. a ``Teeth3DSSegmenter`` here
    once one is trained and bundled. It must keep running locally (PHI), expose
    ``name``/``version``, and return :class:`ToothSegment` objects so the API,
    mesh export, and UI are unaffected.
    """

    return HeuristicArchSegmenter()


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

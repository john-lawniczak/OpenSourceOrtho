"""Data watermark: a traceable, license-bound marker for exported/contributed data.

This is not DRM and cannot force an AI provider or a bad-faith redistributor to
respect the data usage terms - nothing purely technical can, once ordinary STL/
JSON/DICOM-metadata files are shared. What this module provides instead:

- A repo-wide ``CANARY_TOKEN`` embedded verbatim in every artifact this module
  stamps. If that exact string later surfaces in a model's output or in a
  redistributed dataset, that is strong evidence the source was trained on or
  copied OpenSourceOrtho-derived data - the same "canary string" technique used
  by benchmark suites (e.g. BIG-bench) to detect training-set contamination.
  That evidence is what backs a license claim; the watermark is the trail, not
  a lock.
- A per-artifact ``watermark_id`` plus an optional content hash, so a single
  exported file can be tied back to when it was produced.
- A short notice pointing at the actual usage terms, carried in the artifact
  itself so downstream tooling never has to go find the repo to read them.
- A second, hidden layer for STL geometry (``embed_geometry_signature`` /
  ``detect_geometry_signature``): sub-micron vertex nudges that survive a
  casual edit of the visible marker above. See their docstrings for how it
  works and its limits - it is a fallback layer, not a replacement.

See ``docs/DATA_LICENSE.md`` for the terms this backs. This governs *data*
(scans, CBCT metadata, plan/teeth exports); the software itself stays under the
Apache-2.0 license in ``LICENSE``.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field

Vec3 = tuple[float, float, float]
Triangle = tuple[Vec3, Vec3, Vec3]

WATERMARK_SCHEMA = "opensource-ortho-watermark-v1"

# Fixed for the life of the project so every export/contribution carries the
# same literal string. Never regenerate this - a canary only works as
# contamination evidence if it stays constant and rare enough that its
# appearance elsewhere is not plausibly coincidental.
CANARY_TOKEN = "OSO-DATA-CANARY-b7e4b7b4-6b5d-4a0e-9c7a-6a9a9f0e6a3a-DO-NOT-TRAIN"

DATA_LICENSE_NOTICE = (
    "OpenSourceOrtho-exported data. Personal/research use only; no resale, and "
    "no use as AI/ML training or evaluation data without a separate written "
    "license. See docs/DATA_LICENSE.md. " + CANARY_TOKEN
)


class DataWatermark(BaseModel):
    """A traceable record embedded in exported/contributed data artifacts."""

    model_config = {"populate_by_name": True}

    schema_id: str = Field(default=WATERMARK_SCHEMA, alias="schema")
    watermark_id: str
    canary: str = CANARY_TOKEN
    notice: str = DATA_LICENSE_NOTICE
    content_sha256: str | None = None
    # None for deterministic (content-bound) watermarks - see
    # content_bound_watermark - so re-exporting unchanged input still produces
    # byte-identical artifacts. Set to real wall-clock time only where a fresh
    # id is generated per call and reproducibility is not required.
    created_at: datetime | None = None


def new_watermark(content_sha256: str | None = None) -> DataWatermark:
    """A fresh, randomly-identified, timestamped watermark record.

    Use for contributions/exports where each call is a genuinely new event
    (dataset registration, DICOM intake) and reproducibility across repeated
    calls on the same input is not expected.
    """

    return DataWatermark(
        watermark_id=str(uuid.uuid4()),
        content_sha256=content_sha256,
        created_at=datetime.now(timezone.utc),
    )


def content_bound_watermark(seed: str) -> DataWatermark:
    """A watermark whose id is deterministically derived from ``seed``.

    Use this instead of ``new_watermark`` wherever the same input must keep
    producing byte-identical export artifacts (e.g. re-exporting an unchanged
    treatment plan) - a random id (or a wall-clock timestamp) embedded in the
    output would make every export differ even when nothing about the input
    changed. The id still changes whenever ``seed`` (typically the plan id
    plus its content hash) changes, so distinct exports remain distinguishable.
    """

    digest = uuid.uuid5(uuid.NAMESPACE_URL, f"opensource-ortho-watermark:{seed}")
    return DataWatermark(watermark_id=str(digest))


def watermark_block(watermark: DataWatermark) -> dict:
    """JSON-safe dict for embedding a watermark in a manifest/metadata document."""

    return watermark.model_dump(mode="json", by_alias=True)


def stamp_solid_name(name: str, watermark: DataWatermark) -> str:
    """Embed a compact watermark marker into an STL ``solid``/``endsolid`` name.

    ASCII STL treats the solid name as free text, and this repo's own reader
    (``io/stl_import.py``) never parses it, so appending to it is always safe
    for round-tripping. Kept to the id + canary rather than the full notice -
    slicers/CAD tools display this string, and the full notice already lives in
    the sidecar manifest/metadata JSON for this same artifact.
    """

    return f"{name}__oso-wm:{watermark.watermark_id}__{watermark.canary}"


def contains_canary(text: str) -> bool:
    """True if the repo's canary token appears verbatim in ``text``.

    Useful for scanning a third party's output (e.g. a model response, or a
    redistributed dataset) for evidence that it reproduces or was trained on
    OpenSourceOrtho-derived data.
    """

    return CANARY_TOKEN in text


# STL text is written with 6 decimal places (see print_stl.solid_stl). This
# hidden layer treats 3 decimals (0.001 mm, 1 micron) as the "real" geometry
# and uses the finer digits as a payload channel. The magnitude below is
# ~1000x smaller than the smallest feature this project's print export
# considers printable (PrintExportSettings.minimum_printable_feature_mm
# defaults to 0.3mm) and far below any clinical measurement tolerance, so it
# changes nothing observable about the mesh. It is also kept strictly below
# half the carrier's rounding quantum (0.0005mm) so detection - which
# recovers the carrier by rounding a signed vertex back to 3 decimals - never
# crosses a rounding boundary and lands on the wrong carrier.
_SIGNATURE_CARRIER_DECIMALS = 3
GEOMETRY_SIGNATURE_MAGNITUDE_MM = 0.0003


def _round_vertex(vertex: Vec3) -> Vec3:
    # ``round(-0.0001, 3)`` yields -0.0, which formats as the string "-0.000" -
    # a different hash key than the "0.000" a positive-rounding value nearby
    # produces for what is numerically the same carrier. Normalize so embed
    # and detect always derive the identical key for a zero carrier.
    return tuple(
        0.0 if rounded == 0 else rounded
        for rounded in (round(c, _SIGNATURE_CARRIER_DECIMALS) for c in vertex)
    )  # type: ignore[return-value]


def _signature_offset(carrier: Vec3, watermark_id: str) -> Vec3:
    key = f"oso-geom-sig:{watermark_id}:{carrier[0]:.3f}:{carrier[1]:.3f}:{carrier[2]:.3f}"
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    return (
        carrier[0] + ((digest[0] / 255.0) * 2 - 1) * GEOMETRY_SIGNATURE_MAGNITUDE_MM,
        carrier[1] + ((digest[1] / 255.0) * 2 - 1) * GEOMETRY_SIGNATURE_MAGNITUDE_MM,
        carrier[2] + ((digest[2] / 255.0) * 2 - 1) * GEOMETRY_SIGNATURE_MAGNITUDE_MM,
    )


def embed_geometry_signature(triangles: list[Triangle], watermark: DataWatermark) -> list[Triangle]:
    """A hidden, second watermark layer: sub-micron, deterministic vertex nudges.

    Unlike ``stamp_solid_name`` (a plain-text marker anyone can read or strip
    by renaming the solid), this signature lives in the geometry itself -
    invisible in a text editor, in a slicer, or to dimensional inspection. Its
    purpose is redundancy: if someone deletes the visible marker before
    redistributing a file, this layer can still confirm provenance against a
    *candidate* watermark id (see ``detect_geometry_signature``). It does not
    let you blindly recover an id from an unknown file - only verify a guess
    against ids you already track (e.g. ones your own pipeline issued).

    Every occurrence of the SAME original vertex (STL stores vertices
    per-triangle, not deduplicated) gets an IDENTICAL offset, keyed off the
    vertex's own rounded position - this keeps shared edges between adjacent
    triangles coincident so the mesh does not gain seams.

    Best-effort, not indestructible: re-meshing, simplification, or any tool
    that re-quantizes coordinates to fewer than 3 decimal places erases it.
    It is a fallback layered on top of the visible watermark, not a
    replacement for it.
    """

    cache: dict[Vec3, Vec3] = {}
    signed: list[Triangle] = []
    for tri in triangles:
        signed_vertices = []
        for vertex in tri:
            carrier = _round_vertex(vertex)
            if carrier not in cache:
                cache[carrier] = _signature_offset(carrier, watermark.watermark_id)
            signed_vertices.append(cache[carrier])
        signed.append(tuple(signed_vertices))  # type: ignore[arg-type]
    return signed


def detect_geometry_signature(
    triangles: list[Triangle], candidate_watermark_id: str, *, sample_limit: int = 500
) -> float:
    """Fraction of sampled vertices matching the hidden signature for a candidate id.

    This can only confirm or refute a SPECIFIC candidate watermark id - it does
    not extract an id from an unknown mesh. A result near 0.0 means no match
    (wrong id, an un-signed mesh, or geometry altered enough to erase the
    signature); a result near 1.0 is strong evidence the mesh was signed with
    that id (an accidental match across three axes at once is astronomically
    unlikely).
    """

    seen: set[Vec3] = set()
    tolerance_mm = 1e-5
    checked = 0
    hits = 0
    for tri in triangles:
        for vertex in tri:
            carrier = _round_vertex(vertex)
            if carrier in seen:
                continue
            seen.add(carrier)
            expected = _signature_offset(carrier, candidate_watermark_id)
            if all(abs(a - b) <= tolerance_mm for a, b in zip(vertex, expected)):
                hits += 1
            checked += 1
            if checked >= sample_limit:
                return hits / checked
    return hits / checked if checked else 0.0

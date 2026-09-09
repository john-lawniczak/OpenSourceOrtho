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

See ``docs/DATA_LICENSE.md`` for the terms this backs. This governs *data*
(scans, CBCT metadata, plan/teeth exports); the software itself stays under the
Apache-2.0 license in ``LICENSE``.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field

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

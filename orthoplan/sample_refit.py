"""Explicit saved-label refits; original and earlier fit artifacts remain immutable."""

import json

from orthoplan.datasets import SAMPLE_CASE_DIR, SAMPLE_SPECIMEN_ID
from orthoplan.io.mesh_import import read_mesh_geometry
from orthoplan.research_store import records, read_record, save_record
from orthoplan.sample_research_inputs import endpoint_inputs, fit_summary


def refit_status(arch):
    try:
        inputs, _, digest = endpoint_inputs(arch)
        versions = [
            {
                "id": r["id"],
                "created_at": r["created_at"],
                "summary": r["summary"],
                "stale": r["input_digest"] != digest,
            }
            for r in records("fits")
            if r["inputs"]["arch"] == arch
        ]
        return {"ok": True, "inputs": inputs, "input_digest": digest, "versions": versions}
    except (ValueError, OSError, KeyError, TypeError) as exc:
        return {"ok": False, "errors": [str(exc)]}


def open_refit(identity):
    try:
        record = read_record("fits", identity)
        _, _, digest = endpoint_inputs(record["inputs"]["arch"])
        return {"ok": True, "record": record, "stale": record["input_digest"] != digest}
    except (ValueError, OSError, KeyError, TypeError) as exc:
        return {"ok": False, "errors": [str(exc)]}


def refit_payload(payload):
    try:
        arch = payload.get("arch")
        inputs, corrections, digest = endpoint_inputs(arch)
        if payload.get("input_digest") != digest:
            raise ValueError("Saved labels changed. Refresh the inputs before rebuilding.")
        import numpy as np
        from orthoplan.longitudinal.artifact import pack_face_labels
        from orthoplan.longitudinal.preview import build_arch_preview, centered_triangles
        from orthoplan.segmentation.auto import HybridArchSegmenter

        triangles = []
        for source in inputs["sources"]:
            _, vertices = read_mesh_geometry(SAMPLE_CASE_DIR / source["filename"])
            triangles.append(
                centered_triangles(np.asarray(vertices).reshape(-1, 3, 3), source["rotation"])
            )
        preview = build_arch_preview(
            *triangles,
            arch="maxillary" if arch == "upper" else "mandibular",
            segmenter=HybridArchSegmenter(),
            corrections=corrections,
            source_hashes=[s["sha256"] for s in inputs["sources"]],
        )
        preview.update(
            specimen_id=SAMPLE_SPECIMEN_ID,
            sources=inputs["sources"],
            annotation_bindings=inputs["annotations"],
            generator=inputs["generator"],
        )
        pack_face_labels(preview)
        if endpoint_inputs(arch)[2] != digest:
            raise ValueError("Inputs changed while fitting. Rebuild using the latest labels.")
        record = save_fit(inputs, corrections, digest, preview)
        return {"ok": True, "record": record, "stale": False}
    except ImportError:
        return {
            "ok": False,
            "errors": ["Saved-label refitting requires the motion-preview optional dependencies."],
        }
    except (ValueError, OSError, KeyError, TypeError) as exc:
        return {"ok": False, "errors": [str(exc)]}


def save_fit(inputs, corrections, digest, preview):
    arch = inputs["arch"]
    previous = next((r for r in records("fits") if r["inputs"]["arch"] == arch), None)
    original = json.loads((SAMPLE_CASE_DIR / f"derived/progress-01-motion-{arch}.json").read_text())
    record = save_record(
        "fits",
        {
            "schema": "ortho-saved-label-fit-v1",
            "inputs": inputs,
            "input_digest": digest,
            "reference_snapshots": corrections,
            "preview": preview,
            "summary": fit_summary(preview),
            "previous_id": previous["id"] if previous else None,
            "comparison": {
                "original": fit_summary(original),
                "previous": previous["summary"] if previous else None,
            },
            "limitations": "Contributor-label fit; residuals measure surface agreement, not motion accuracy.",
        },
    )
    return record

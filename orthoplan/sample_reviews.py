"""Per-tooth contributor reviews bind to the scan and the exact region mask."""

import base64
import hashlib

from orthoplan.region_corrections import baseline_source
from orthoplan.research_store import records, save_record


def tooth_bindings(correction):
    labels = base64.b64decode(correction["labels_base64"], validate=True)
    return {
        str(tooth): hashlib.sha256(bytes(label == tooth for label in labels)).hexdigest()
        for tooth in sorted(set(labels) - {0})
    }


def reviews_for(correction):
    bindings = tooth_bindings(correction)
    latest = {}
    for record in records("reviews"):
        tooth = record["tooth"]
        if (
            record["source_sha256"] == correction["source_sha256"]
            and record["mask_sha256"] == bindings.get(tooth)
            and tooth not in latest
        ):
            latest[tooth] = record
    return bindings, latest


def save_tooth_review(payload):
    from orthoplan.sample_teeth import sample_annotation

    try:
        arch, visit = payload.get("arch"), payload.get("visit", "initial")
        source = baseline_source(arch, visit)
        correction, _ = sample_annotation(arch, visit)
        bindings = tooth_bindings(correction)
        tooth = str(payload.get("tooth"))
        if (
            tooth not in bindings
            or payload.get("source_sha256") != source["sha256"]
            or payload.get("mask_sha256") != bindings[tooth]
        ):
            raise ValueError(
                "The tooth or scan changed. Reload its painting before recording review."
            )
        if payload.get("status") not in {"checked", "uncertain", "unchecked"}:
            raise ValueError("Choose checked, uncertain or unchecked")
        fields = {}
        for key, limit in [("reviewer", 120), ("notes", 2000)]:
            value = payload.get(key, "")
            if not isinstance(value, str) or len(value) > limit:
                raise ValueError("Review text exceeds its limit")
            fields[key] = value.strip()
        record = save_record(
            "reviews",
            {
                "schema": "ortho-tooth-review-v1",
                "arch": arch,
                "visit": visit,
                "tooth": tooth,
                "source_sha256": source["sha256"],
                "mask_sha256": bindings[tooth],
                "status": payload["status"],
                "role": "contributor",
                **fields,
            },
        )
        return {"ok": True, "review": record}
    except (ValueError, TypeError, OSError, KeyError) as exc:
        return {"ok": False, "errors": [str(exc)]}

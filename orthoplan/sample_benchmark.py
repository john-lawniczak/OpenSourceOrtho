"""Compare bundled automatic labels with a frozen contributor painting, not truth."""

import base64
import json
import hashlib
from collections import Counter
from time import monotonic

from orthoplan.datasets import SAMPLE_CASE_DIR
from orthoplan.research_store import save_record
from orthoplan.sample_research_inputs import endpoint_inputs


def label_agreement(reference, prediction):
    if len(reference) != len(prediction) or not reference:
        raise ValueError("Label arrays must cover the same nonempty source mesh")
    rows = []
    for tooth in sorted((set(reference) | set(prediction)) - {0}):
        expected = sum(value == tooth for value in reference)
        proposed = sum(value == tooth for value in prediction)
        overlap = sum(a == tooth and b == tooth for a, b in zip(reference, prediction))
        union = expected + proposed - overlap
        confusion = Counter(b for a, b in zip(reference, prediction) if a == tooth)
        rows.append(
            {
                "automatic_labels_on_reference_faces": {
                    str(key): count for key, count in sorted(confusion.items())
                },
                "tooth": str(tooth),
                "reference_faces": expected,
                "predicted_faces": proposed,
                "intersection_faces": overlap,
                "iou": overlap / union if union else None,
                "precision": overlap / proposed if proposed else None,
                "recall": overlap / expected if expected else None,
            }
        )
    painted = sum(bool(value) for value in reference)
    return {
        "face_count": len(reference),
        "reference_painted_faces": painted,
        "same_identity_faces": sum(a == b and a != 0 for a, b in zip(reference, prediction)),
        "unlabeled_reference_predicted_faces": sum(
            a == 0 and b != 0 for a, b in zip(reference, prediction)
        ),
        "missing_reference_teeth": [
            r["tooth"] for r in rows if r["reference_faces"] and not r["predicted_faces"]
        ],
        "per_tooth": rows,
        "macro_iou": sum(r["iou"] for r in rows) / len(rows) if rows else None,
    }


def benchmark_payload(payload):
    started = monotonic()
    try:
        arch = payload.get("arch")
        inputs, corrections, digest = endpoint_inputs(arch)
        if payload.get("input_digest") != digest:
            raise ValueError("Saved labels changed. Refresh before comparing.")
        raw = (SAMPLE_CASE_DIR / f"derived/progress-01-motion-{arch}.json").read_bytes()
        prediction = json.loads(raw)
        reports = compare_artifact(prediction, corrections, inputs["annotations"])
        record = save_record(
            "benchmarks",
            {
                "schema": "ortho-contributor-agreement-v1",
                "inputs": inputs,
                "input_digest": digest,
                "reference_snapshots": corrections,
                "prediction_sha256": hashlib.sha256(raw).hexdigest(),
                "prediction_segmenter": prediction.get("segmenter"),
                "reports": reports,
                "independent_accuracy": None,
                "boundary_distance": None,
                "correction_time_seconds": None,
                "segmentation_runtime_seconds": None,
                "comparison_runtime_seconds": monotonic() - started,
                "limitations": "Face-count agreement with contributor painting, not independent accuracy. Unpainted faces are unknown, not confirmed gum. No surface-area weighting or boundary-distance measurement.",
            },
        )
        return {"ok": True, "record": record}
    except (ValueError, OSError, KeyError, TypeError) as exc:
        return {"ok": False, "errors": [str(exc)]}


def compare_artifact(prediction, corrections, annotations):
    mapping = {t["face_label"]: int(t["tooth"]) for t in prediction["teeth"]}
    reports = []
    for i, correction in enumerate(corrections):
        if correction is None:
            reports.append({"visit": annotations[i]["visit"], "status": "no-contributor-labels"})
            continue
        if prediction["sources"][i]["sha256"] != correction["source_sha256"]:
            raise ValueError("Automatic labels belong to another scan")
        key = "moving_face_labels_base64" if i == 0 else "target_face_labels_base64"
        labels = base64.b64decode(prediction[key], validate=True)
        # Target regions can have different IDs; use the artifact's explicit mapping.
        target_mapping = {
            t["face_label"]: int(t["target_tooth"])
            for t in prediction["teeth"]
            if t.get("target_tooth")
        }
        proposed = bytes((mapping if i == 0 else target_mapping).get(value, 0) for value in labels)
        reports.append(
            {
                "visit": annotations[i]["visit"],
                "status": "compared",
                **label_agreement(
                    base64.b64decode(correction["labels_base64"], validate=True), proposed
                ),
            }
        )
    return reports

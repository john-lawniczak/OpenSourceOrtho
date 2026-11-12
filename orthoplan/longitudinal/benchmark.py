"""Accuracy scoring against independently supplied, source-bound reviewed truth."""
from __future__ import annotations

import base64
import numpy as np
from scipy.spatial.transform import Rotation


def _labels(record, key):
    value = record.get(key)
    return np.array(value, dtype=int) if isinstance(value, list) else np.frombuffer(base64.b64decode(value, validate=True), dtype=np.uint8)


def score_motion(preview, truth):
    if truth.get("schema") != "ortho-motion-truth-v1" or truth.get("frame") != preview["frame"]:
        raise ValueError("Truth and prediction need the same explicit coordinate frame")
    if truth.get("source_hashes") != [s["sha256"] for s in preview["sources"]]:
        raise ValueError("Ground truth is not bound to these endpoint scans")
    review = truth.get("review", {})
    if truth.get("kind") not in ["synthetic", "reviewed-real", "reviewed-repeat"]:
        raise ValueError("Declare synthetic, reviewed-real, or reviewed-repeat truth")
    if truth["kind"] != "synthetic" and not (isinstance(review.get("reviewer"), str) and review["reviewer"].strip() and all(review.get(k) is True for k in ["boundaries", "correspondence", "poses"])):
        raise ValueError("Real benchmark truth requires independent boundary, correspondence and pose review")
    expected = {str(t["tooth"]): t for t in truth["teeth"]}
    predicted = {str(t["tooth"]): t for t in preview["teeth"]}
    if "target_face_labels_base64" in preview:
        ownership = _labels(preview, "target_face_labels_base64")
        predicted = {key: {**t, "target_faces": np.flatnonzero(ownership == t["face_label"]).tolist()}
                     for key, t in predicted.items()}
    rows = [_score_tooth(tooth, predicted.get(key), truth) for key, tooth in expected.items()]
    valid = [r for r in rows if r["translation_error"] is not None]
    return {
        "kind": truth["kind"], "units": truth["units"], "teeth": rows,
        "expected_regions": len(rows), "evaluated_regions": len(valid),
        "missing_regions": len(rows) - len(valid),
        "translation_rmse": float(np.sqrt(np.mean([r["translation_error"] ** 2 for r in valid]))) if valid else None,
        "rotation_mean_error_deg": float(np.mean([r["rotation_error_deg"] for r in valid])) if valid else None,
        "identity_errors": sum(r["identity_correct"] is False for r in rows),
        "identity_evaluated": sum(r["identity_correct"] is not None for r in rows),
        "false_motion_regions": sum(r["false_motion"] is True for r in rows),
        "source_boundary_accuracy": _boundary_accuracy(preview, truth),
        "boundary_regions": boundary_regions(preview, truth),
        "fit_coverage": len(valid)/len(rows) if rows else 0,
    }


def _score_tooth(truth_tooth, candidate, truth):
    row = {"tooth": str(truth_tooth["tooth"]), "translation_error": None,
           "rotation_error_deg": None, "identity_correct": None, "false_motion": None}
    if not candidate or candidate["status"] == "held-unmatched":
        return row
    rq = Rotation.from_quat(candidate["quaternion_xyzw"])
    tq = Rotation.from_quat(truth_tooth["quaternion_xyzw"])
    pivot = np.asarray(truth_tooth["pivot"])
    cp = np.asarray(candidate["pivot"])
    predicted_end = rq.apply(pivot - cp) + cp + candidate["translation"]
    actual_end = pivot + truth_tooth["translation"]
    error = float(np.linalg.norm(predicted_end - actual_end))
    rotation_error = float(np.degrees((rq * tq.inv()).magnitude()))
    row.update(translation_error=error, rotation_error_deg=rotation_error)
    # Score *independent target face labels*, never the algorithm's self-assigned target ID.
    faces = candidate.get("target_faces")
    if faces is not None and len(faces) and "target_face_tooth_ids" in truth:
        target_labels = _labels(truth, "target_face_tooth_ids")[faces]
        ids, counts = np.unique(target_labels, return_counts=True)
        row["identity_correct"] = int(ids[np.argmax(counts)]) == int(truth_tooth["target_tooth"])
    if truth["kind"] == "reviewed-repeat" or truth.get("no_motion"):
        row["false_motion"] = bool(np.linalg.norm(predicted_end - pivot) > truth["translation_tolerance"]
                                   or np.degrees(rq.magnitude()) > truth["rotation_tolerance_deg"])
    return row


def _boundary_accuracy(preview, truth):
    expected = _labels(truth, "source_face_tooth_ids")
    labels = _labels(preview, "moving_face_labels_base64")
    if len(expected) != len(labels):
        raise ValueError("Source boundary labels have the wrong face count")
    mapping = {t["face_label"]: int(t["tooth"]) for t in preview["teeth"]}
    actual = np.array([mapping.get(int(i), 0) for i in labels])
    crown = expected != 0
    return float(np.mean(actual[crown] == expected[crown])) if crown.any() else None


def boundary_regions(preview, truth):
    expected = _labels(truth, "source_face_tooth_ids")
    ownership = _labels(preview, "moving_face_labels_base64")
    if expected.shape != ownership.shape:
        raise ValueError("Boundary label counts differ")
    mapping = {t["face_label"]: int(t["tooth"]) for t in preview["teeth"]}
    actual = np.array([mapping.get(int(i), 0) for i in ownership])
    result = []
    for tooth in sorted((set(expected) | set(actual)) - {0}):
        true, predicted = expected == tooth, actual == tooth
        intersection = int(np.count_nonzero(true & predicted))
        union = int(np.count_nonzero(true | predicted))
        result.append({"tooth": str(tooth), "iou": intersection/union,
                       "precision": intersection/int(predicted.sum()) if predicted.any() else None,
                       "recall": intersection/int(true.sum()) if true.any() else None,
                       "false_positive_faces": int(np.count_nonzero(predicted & ~true)),
                       "missed_faces": int(np.count_nonzero(true & ~predicted))})
    return result

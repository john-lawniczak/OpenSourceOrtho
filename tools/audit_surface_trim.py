"""Audit a trim-only repair bundle against its source STL and prior labels."""
import argparse
import base64
import hashlib
import json
from pathlib import Path

import numpy as np


def audit_trim(bundle, source, prior_labels):
    """Verify retained binary records and quantify removals without certifying anatomy."""
    edited = base64.b64decode(bundle["stlBase64"], validate=True)
    scan, repair = bundle["scan"], bundle["scan"]["repair"]
    if repair["patches"]:
        raise ValueError("This audit supports trim-only copies.")
    source_hash, edited_hash = hashlib.sha256(source).hexdigest(), hashlib.sha256(edited).hexdigest()
    if source_hash != repair["sourceSha256"] or edited_hash != scan["sha256"]:
        raise ValueError("Source or edited STL hash mismatch.")
    arrays = []
    for data in (source, edited):
        count = int.from_bytes(data[80:84], "little")
        if len(data) != 84 + count * 50 or count < 1:
            raise ValueError("Expected complete binary STL face records.")
        arrays.append(np.frombuffer(data, offset=84, dtype="V50"))
    original, retained = arrays
    keep = np.zeros(len(original), bool)
    index = 0
    for face_index, face in enumerate(original):
        if index < len(retained) and face == retained[index]:
            keep[face_index] = True
            index += 1
    if index != len(retained):
        raise ValueError("Edited faces are not an ordered exact subset of the source.")
    labels = []
    for record, digest, count in ((prior_labels, source_hash, len(original)),
                                  (bundle["labels"], edited_hash, len(retained))):
        values = np.frombuffer(base64.b64decode(record["labels_base64"], validate=True), dtype=np.uint8)
        if record["source_sha256"] != digest or record["face_count"] != count or len(values) != count:
            raise ValueError("Labels do not match their surface.")
        labels.append(values)
    before, after = labels
    dtype = np.dtype([("normal", "<f4", (3,)), ("vertices", "<f4", (3, 3)), ("attribute", "<u2")])
    faces = np.frombuffer(source, offset=84, dtype=dtype)["vertices"]
    if not np.isfinite(faces).all():
        raise ValueError("Source has non-finite geometry.")
    areas = np.linalg.norm(np.cross(faces[:, 1]-faces[:, 0], faces[:, 2]-faces[:, 0]), axis=1)/2
    removed = ~keep
    return {
        "source_sha256": source_hash, "edited_sha256": edited_hash,
        "source_faces": len(original), "edited_faces": len(retained),
        "removed_faces": int(removed.sum()), "retained_face_records_exact": True,
        "label_changes_on_retained_faces": int((before[keep] != after).sum()),
        "removed_by_prior_label": {str(k): int(((before == k) & removed).sum()) for k in np.unique(before)},
        "prior_tooth_surface_area_removed_fraction": {
            str(k): float(areas[(before == k) & removed].sum()/areas[before == k].sum())
            if areas[before == k].sum() > 0 else None for k in np.unique(before) if k},
        "all_present_labels_retained": sorted(map(int, np.unique(after[after != 0]))),
        "removed_bounds": [faces[removed].min(axis=(0, 1)).tolist(), faces[removed].max(axis=(0, 1)).tolist()] if removed.any() else None,
        "assessment": "Unreviewed cleanup copy. Labels are drafts; unlabeled removal does not prove tooth preservation.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("source", type=Path)
    parser.add_argument("prior_labels", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit_trim(json.loads(args.bundle.read_text()), args.source.read_bytes(), json.loads(args.prior_labels.read_text()))
    args.output.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()

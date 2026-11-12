"""Source-bound face-label corrections; pose estimates never inherit review status."""
import base64
import numpy as np
from orthoplan.segmentation.heuristic import ToothSegment


def correction_segments(record, triangles, sha256, arch):
    expected_arch = "upper" if arch == "maxillary" else "lower"
    if record.get("schema") != "ortho-region-corrections-v1" or record.get("source_sha256") != sha256:
        raise ValueError("Corrections must match the exact source hash")
    if record.get("face_count") != len(triangles) or record.get("arch") != expected_arch:
        raise ValueError("Correction face count or arch mismatch")
    labels = np.frombuffer(base64.b64decode(record["labels_base64"], validate=True), dtype=np.uint8)
    allowed = {0, *([q * 10 + n for q in ([1, 2] if expected_arch == "upper" else [3, 4]) for n in range(1, 9)])}
    if len(labels) != len(triangles) or not set(labels).issubset(allowed):
        raise ValueError("Invalid correction labels")
    segments = []
    for tooth in sorted(set(labels) - {0}):
        faces = triangles[labels == tooth]
        if len(faces) < 4:
            raise ValueError("Each corrected tooth needs at least four faces")
        segments.append(ToothSegment(str(tooth), [tuple(map(tuple, face)) for face in faces],
                                     tuple(faces.mean(axis=(0, 1))), 0.5))
    if not segments:
        raise ValueError("Corrections contain no labeled teeth")
    return segments

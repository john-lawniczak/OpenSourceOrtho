"""Fit paired original-STL and CBCT patient-LPS landmarks for explicit review."""

import hashlib
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from orthoplan.imaging.landmark_registration import landmark_proposal  # noqa:E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pairs", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-scan", type=Path, required=True)
    parser.add_argument("--volume-packet", type=Path, required=True)
    args = parser.parse_args()
    packet = json.loads(args.pairs.read_text())
    if (
        packet.get("source_scan_sha256")
        != hashlib.sha256(args.source_scan.read_bytes()).hexdigest()
    ):
        raise ValueError("Landmark source hash does not match the supplied STL")
    if packet.get("volume_source_digest") != json.loads(args.volume_packet.read_text()).get(
        "source_digest"
    ):
        raise ValueError("Landmark volume digest does not match the supplied packet")
    result = landmark_proposal(packet)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print("Unaccepted landmark proposal written; review the held-out errors and coordinate frames.")


if __name__ == "__main__":
    main()

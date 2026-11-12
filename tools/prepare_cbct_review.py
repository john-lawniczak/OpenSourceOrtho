"""Prepare a private local DICOM review packet; never publish raw pixels."""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from orthoplan.imaging.dicom_volume import build_review_packet  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dicom_directory", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stride", type=int, default=4)
    args = parser.parse_args()
    packet = build_review_packet(args.dicom_directory, stride=args.stride)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(packet, separators=(",", ":")) + "\n")
    print(
        json.dumps(
            {
                key: packet[key]
                for key in [
                    "dimensions_xyz",
                    "source_slices",
                    "excluded_series",
                    "stride",
                    "status",
                ]
            }
        )
    )


if __name__ == "__main__":
    main()

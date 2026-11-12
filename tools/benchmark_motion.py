"""Score local endpoint predictions against separately reviewed truth manifests."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from orthoplan.longitudinal.benchmark import score_motion  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    rows = []
    for case in manifest.get("cases", []):
        root = args.manifest.parent
        prediction = json.loads((root / case["prediction"]).read_text())
        truth = json.loads((root / case["truth"]).read_text())
        rows.append({"case_id": case["case_id"], **score_motion(prediction, truth)})
    args.output.write_text(json.dumps({"cases": rows, "real_case_count": sum(r["kind"] != "synthetic" for r in rows)}, indent=2) + "\n")
    print(f"Scored {len(rows)} cases; no missing truth was synthesized.")


if __name__ == "__main__":
    main()

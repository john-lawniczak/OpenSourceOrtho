"""Review contributed capture provenance against the original local scan bytes."""
import hashlib
import json
from pathlib import Path
import sys

from orthoplan.evaluation.capture_review import review_manifest
from orthoplan.model.dataset import read_manifest


def add_capture_parser(sub):
    parser = sub.add_parser("review-captures", help="verify scan hashes and review acquisition provenance")
    parser.add_argument("manifest", help="contribution manifest with optional scan acquisition records")
    parser.add_argument("--out", help="write a research-only JSON review")


def cmd_review_captures(args):
    try:
        source = Path(args.manifest).resolve()
        manifest = read_manifest(source)
        protected = {source}
        for scan in manifest.scans:
            path = source.parent / scan.filename
            if path.is_symlink() or not path.resolve().is_relative_to(source.parent):
                raise ValueError("Scan references must remain inside the manifest directory")
            if hashlib.sha256(path.read_bytes()).hexdigest() != scan.sha256:
                raise ValueError(f"Scan hash mismatch: {scan.filename}")
            protected.add(path.resolve())
        review = review_manifest(manifest)
        review["scan_hashes_verified"] = True
        body = json.dumps(review, indent=2) + "\n"
        if args.out:
            output = Path(args.out)
            if output.resolve() in protected:
                raise ValueError("Review output must not overwrite the manifest or a source scan")
            output.write_text(body)
        else:
            print(body, end="")
        return 0
    except (OSError, ValueError) as error:
        print(f"review-captures error: {error}", file=sys.stderr)
        return 2

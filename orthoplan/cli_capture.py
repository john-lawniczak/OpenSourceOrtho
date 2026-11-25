"""Review contributed capture provenance against the original local scan bytes."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile

from orthoplan.evaluation.capture_review import review_manifest
from orthoplan.model.dataset import read_manifest


def add_capture_parser(sub):
    parser = sub.add_parser("review-captures", help="verify scan hashes and review acquisition provenance")
    parser.add_argument("manifest", help="contribution manifest with optional scan acquisition records")
    parser.add_argument("--out", help="write a research-only JSON review")


def _write_review(output, body, protected):
    if output.resolve() in protected or (output.exists() and any(
            output.samefile(source) for source in protected)):
        raise ValueError("Review output must not overwrite the manifest or a source scan")
    # Replace the directory entry, never truncate an existing inode or follow a
    # destination symlink. A failed write also leaves any previous report intact.
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=output.parent,
                                         prefix=".capture-review-", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(body)
        temporary.replace(output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def cmd_review_captures(args):
    try:
        source = Path(args.manifest).resolve()
        manifest = read_manifest(source)
        protected = {source}
        for scan in manifest.scans:
            path = source.parent / scan.filename
            if path.is_symlink() or not path.resolve().is_relative_to(source.parent):
                raise ValueError("Scan references must remain inside the manifest directory")
            with path.open("rb") as handle:
                digest = hashlib.file_digest(handle, "sha256").hexdigest()
            if digest != scan.sha256:
                raise ValueError(f"Scan hash mismatch: {scan.filename}")
            protected.add(path.resolve())
        review = review_manifest(manifest)
        review["scan_hashes_verified"] = True
        body = json.dumps(review, indent=2) + "\n"
        if args.out:
            _write_review(Path(args.out), body, protected)
        else:
            print(body, end="")
        return 0
    except (OSError, ValueError) as error:
        print(f"review-captures error: {error}", file=sys.stderr)
        return 2

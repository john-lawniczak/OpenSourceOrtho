"""Regenerate the public case catalog and the browser's sample reference."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orthoplan.dataset_catalog import build_catalog, browser_sample_module, catalog_readme  # noqa: E402
from orthoplan.datasets import DATASETS_ROOT  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    catalog = build_catalog()
    outputs = {
        DATASETS_ROOT / "index.json": json.dumps(catalog, indent=2) + "\n",
        DATASETS_ROOT / "README.md": catalog_readme(catalog),
        ROOT / "ui/sample-dataset.js": browser_sample_module(catalog),
    }
    stale = []
    for path, text in outputs.items():
        if args.check:
            if not path.exists() or path.read_text() != text:
                stale.append(str(path.relative_to(ROOT)))
        else:
            path.write_text(text)
    if stale:
        print("Stale generated catalog files: " + ", ".join(stale))
        return 1
    print("Dataset catalog verified." if args.check else "Dataset catalog generated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

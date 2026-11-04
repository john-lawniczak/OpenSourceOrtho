"""Private process entry point; isolates disposable geometry caches from the server."""

import json
import sys
from pathlib import Path


def main():
    from orthoplan.api import evaluate_plan_payload
    from orthoplan.segmentation_api import segment_payload

    source, destination = map(Path, sys.argv[1:])
    request = json.loads(source.read_text())
    workspace = Path(request["workspace"])
    try:
        if request["operation"] == "segment":
            result = segment_payload(
                request["payload"], workspace=workspace, ui_dir=Path(request["ui_dir"])
            )
        else:
            result = evaluate_plan_payload(request["payload"], workspace=workspace)
    except Exception:
        result = {"ok": False, "errors": ["Geometry worker failed. Check the input and retry."]}
    destination.write_text(json.dumps(result))


if __name__ == "__main__":
    main()

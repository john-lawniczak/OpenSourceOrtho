"""Optional private sample discussion brief; never converted into movements."""
import json
from pathlib import Path

from orthoplan.datasets import SAMPLE_CASE_DIR


def sample_plan_brief_payload(root: Path | None = None) -> dict:
    path = (root or SAMPLE_CASE_DIR) / "private" / "plan-brief.json"
    try:
        if not path.exists():
            return {"ok": True, "available": False, "text": ""}
        record = json.loads(path.read_text())
        if (record.get("schema") != "ortho-plan-brief-v1"
                or not isinstance(record.get("text"), str) or len(record["text"]) > 8000):
            raise ValueError("Invalid plan brief")
        return {"ok": True, "available": True, "text": record["text"]}
    except (OSError, ValueError, AttributeError):
        return {"ok": False, "errors": ["Could not load the sample discussion brief."]}

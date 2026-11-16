"""The explicitly selected local USER_ONE trim, without publishing its annotations."""

import base64
import hashlib
import json

from orthoplan.datasets import SAMPLE_CASE_DIR

# Bind the selected cleanup version; never silently use a newer repair or painting.
LOWER_CLEAN_SHA256 = "6ed235820a8ebfe91ac686adfac297e30c1b363faadfcce3ce2c427962628b9e"
LOWER_SOURCE_SHA256 = "fe3668a01e8e6f999e613d8a2ee334c7283263e6af7ad61effae37af6a75a4b6"


def local_history_surface():
    path = SAMPLE_CASE_DIR / "private/surface-edits/week-18-lower-cleaned/repair-bundle.json"
    if not path.is_file():
        return {"available": False}
    record = json.loads(path.read_text())
    scan = record["scan"]
    repair = scan["repair"]
    raw = base64.b64decode(record["stlBase64"], validate=True)
    if (scan["arch"] != "lower" or scan["sha256"] != LOWER_CLEAN_SHA256
            or hashlib.sha256(raw).hexdigest() != LOWER_CLEAN_SHA256
            or repair["sourceSha256"] != LOWER_SOURCE_SHA256 or repair["patches"]
            or repair["sourceCapture"] != "fusion-h-4" or repair["sourceVisit"] != "progress-02"):
        raise ValueError("The selected week 18 trim does not match its recorded source/version")
    # Do not send contributor painting, notes, or the rest of the private bundle.
    return {"available": True, "sha256": LOWER_CLEAN_SHA256,
            "source_sha256": LOWER_SOURCE_SHA256, "filename": scan["filename"],
            "stl_base64": record["stlBase64"]}

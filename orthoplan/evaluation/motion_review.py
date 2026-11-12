"""Local, evidence-bound explanations of endpoint fits; no provider or geometry access."""

import math
import re

from orthoplan.evaluation.finding import (
    Finding,
    FindingCategory,
    FindingProvenance,
    FindingSeverity,
    lint_finding,
)


def _number(value):
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
    ):
        raise ValueError("Fit evidence must contain finite nonnegative numbers")
    return value


def _region(raw):
    tooth, status = raw.get("tooth"), raw.get("status")
    if not isinstance(tooth, str) or not re.fullmatch(r"[1-4][1-8]", tooth):
        raise ValueError("Fit evidence needs FDI region labels")
    if status not in {"estimated-draft", "estimated-weak", "held-unmatched"}:
        raise ValueError("Unknown fitted region status")
    delta = raw.get("translation")
    if not isinstance(delta, list) or len(delta) != 3:
        raise ValueError("Fit evidence needs three translation coordinates")
    shift = math.hypot(*[_number(abs(v)) for v in delta])
    fit = raw.get("fit") or {}
    residual = None if fit.get("p90_residual") is None else _number(fit["p90_residual"])
    consistency = fit.get("consistency") or {}
    return {
        "tooth": tooth,
        "status": status,
        "pivot_shift": shift,
        "p90_residual": residual,
        "sampling_shift": None
        if consistency.get("sampling_shift") is None
        else _number(consistency["sampling_shift"]),
        "cycle_shift": None
        if consistency.get("round_trip_shift") is None
        else _number(consistency["round_trip_shift"]),
    }


def _finding(title, message, reference):
    return lint_finding(
        Finding(
            severity=FindingSeverity.INFO,
            category=FindingCategory.EDUCATION,
            provenance=FindingProvenance.MODEL,
            title=title,
            message=message,
            reference=reference,
        )
    ).model_dump(mode="json")


def motion_review_payload(payload):
    """Ignore caller prose; explain only bounded, validated numeric/status evidence."""
    try:
        raw = payload.get("teeth")
        if not isinstance(raw, list) or not 1 <= len(raw) <= 32:
            raise ValueError("Provide 1–32 fitted regions")
        rows = [_region(record) for record in raw]
        if len({row["tooth"] for row in rows}) != len(rows):
            raise ValueError("Duplicate fitted regions")
        unit = payload.get("unit")
        if unit not in {"mm", "cm", "in", "scan units"}:
            raise ValueError("Unknown fit units")
        return _report(rows, unit)
    except (ValueError, TypeError, AttributeError, OverflowError) as exc:
        return {"ok": False, "errors": [str(exc)]}


def _report(rows, unit):
    held = [r["tooth"] for r in rows if r["status"] == "held-unmatched"]
    weak = [r["tooth"] for r in rows if r["status"] == "estimated-weak"]
    measured = [r for r in rows if r["status"] != "held-unmatched"]
    ranked = sorted(
        measured,
        key=lambda r: (
            r["status"] == "estimated-weak",
            r["p90_residual"] if r["p90_residual"] is not None else math.inf,
        ),
        reverse=True,
    )
    findings = [
        _finding(
            "What the fit contains",
            f"{len(measured)} of {len(rows)} draft regions have an estimated pose; {len(weak)} are weak and {len(held)} are held. A held region's zero movement means no usable estimate, not a stationary tooth.",
            "Basis: region status fields",
        ),
        _finding(
            "What to review next",
            f"Inspect boundaries and endpoint matches for regions {', '.join(held + [r['tooth'] for r in ranked])}. Surface residuals measure geometric agreement; they do not establish tooth identity. Compare the fitted endpoint with the recorded scan after each correction.",
            "Basis: held first, then weak status and descending p90 residual",
        ),
        _finding(
            "What these numbers cannot establish",
            f"Reported distances use {unit}; a declared scale still needs verification. Reverse-fit and sampling differences expose sensitivity, not calibrated uncertainty. Weeks 2–6 use timing assumptions between two endpoints; they do not measure actual weekly progress.",
            "Basis: two-visit fitting and interpolation contract",
        ),
    ]
    return {
        "ok": True,
        "mode": "deterministic-local-helper",
        "provider_used": False,
        "units": unit,
        "regions": rows,
        "review_order": held + [r["tooth"] for r in ranked],
        "findings": findings,
        "evidence_scope": "Supplied fit metadata; raw scans and anatomy were not inspected",
    }

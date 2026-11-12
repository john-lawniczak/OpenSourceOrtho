import pytest

pytest.importorskip("numpy")
pytest.importorskip("scipy")
from orthoplan.validation.motion_stress import run_stress_benchmark  # noqa: E402


def test_known_geometry_recovery_and_repeat_scan_false_motion_are_reported():
    report = run_stress_benchmark(range(2))
    assert report["real_accuracy"] is None
    assert len(report["cases"]) == 12
    exact = [r for r in report["cases"] if r["condition"] in ["exact-repeat", "known-motion"]]
    assert max(r["translation_error_mm"] for r in exact) < 1e-5
    assert max(r["rotation_error_deg"] for r in exact) < 1e-4
    # Independently resampled surfaces can invent rotation despite no true motion.
    repeated = next(r for r in report["summaries"] if r["condition"] == "resampled-repeat")
    assert repeated["false_motion_cases"] > 0
    assert repeated["rotation_mean_error_deg"] > 1
    assert all("sampling_shift" in r["consistency"] for r in report["cases"])

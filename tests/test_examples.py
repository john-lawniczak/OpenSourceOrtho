from __future__ import annotations

from pathlib import Path

from examples.generate_examples import basic_plan, segmented_plan
from examples.generate_north_star import _seed_plan
from orthoplan.api import evaluate_plan
from orthoplan.generation import generate_plan_payload
from orthoplan.io.serialization import plan_to_json, read_plan

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def test_checked_in_examples_match_generator() -> None:
    # If the model changes, regenerate: `python examples/generate_examples.py`.
    assert (EXAMPLES / "basic_plan.json").read_text(encoding="utf-8") == plan_to_json(basic_plan())
    assert (EXAMPLES / "segmented_plan.json").read_text(encoding="utf-8") == plan_to_json(
        segmented_plan()
    )


def test_basic_example_loads_and_trips_a_cap() -> None:
    result = evaluate_plan(read_plan(EXAMPLES / "basic_plan.json"))
    assert result["ok"] is True
    assert any("linear cap" in finding["title"] for finding in result["findings"])


def test_north_star_generates_consistent_mild_plan() -> None:
    # The North Star demonstrates Generate Plan end-to-end on the first specimen.
    result = generate_plan_payload({"plan": _seed_plan().model_dump(mode="json")})
    assert result["ok"] is True
    assert result["source"] == "authored"
    assert result["correctness"]["verdict"] == "CONSISTENT"
    assert result["correctness"]["cap_violations"] == 0
    months = result["timeline"]["projected_duration_days"] / 30
    assert 4 <= months <= 6  # a minimal-to-medium case


def test_north_star_committed_plan_loads() -> None:
    # Regenerate with `python examples/generate_north_star.py` if the model changes.
    result = evaluate_plan(read_plan(EXAMPLES / "north_star_canonical_plan.json"))
    assert result["ok"] is True
    assert result["timeline"]["stage_count"] == 10
    assert result["scale_confirmed"] is True


def test_segmented_example_exposes_approximate_frame_without_rendering_rotation() -> None:
    result = evaluate_plan(read_plan(EXAMPLES / "segmented_plan.json"))
    assert result["ok"] is True
    assert "11" in result["tooth_frames"]
    assert result["tooth_frames"]["11"]["approximate"] is True
    assert result["frames"][0]["poses"][0]["rotation_renderable"] is False

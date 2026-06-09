from __future__ import annotations

import json
from pathlib import Path

import pytest

from orthoplan.arch_contract import arch_from_tooth_value, infer_arch_from_name, normalize_arch_label
from orthoplan.generation import generate_plan_payload
from orthoplan.model import AxisCaps, MovementCaps, ToothId

ROOT = Path(__file__).resolve().parents[1]


def test_mobile_lite_request_validates_against_engine() -> None:
    payload = json.loads((ROOT / "mobile/fixtures/lite_generate_request.json").read_text())

    result = generate_plan_payload(payload)

    assert result["ok"] is True
    assert result["source"] == "educational-synthetic"
    assert result["requires_acknowledgement"] is False
    assert result["correctness"]["verdict"] == "CONSISTENT"


def test_arch_contract_normalizes_shared_labels_and_filenames() -> None:
    assert normalize_arch_label("upper") == "maxillary"
    assert normalize_arch_label("lower") == "mandibular"
    assert normalize_arch_label("maxillary") == "maxillary"
    assert normalize_arch_label("mandibular") == "mandibular"
    assert normalize_arch_label("unknown") is None
    assert infer_arch_from_name("sample-test-case-upper.stl") == "maxillary"
    assert infer_arch_from_name("scan_l.stl") == "mandibular"
    assert infer_arch_from_name("scan.stl") is None
    assert arch_from_tooth_value("11") == "maxillary"
    assert arch_from_tooth_value("38") == "mandibular"


@pytest.mark.parametrize("value", ["11", "48", "27"])
def test_fdi_contract_accepts_two_digit_1_to_8_values(value: str) -> None:
    assert ToothId(value=value).value == value


@pytest.mark.parametrize("value", ["99", "9", "ab", "", "111", "10"])
def test_fdi_contract_rejects_values_outside_two_digit_1_to_8(value: str) -> None:
    with pytest.raises(ValueError):
        ToothId(value=value)


def test_movement_cap_override_contract_uses_same_fdi_key_rules() -> None:
    MovementCaps(per_tooth_overrides={"11": AxisCaps(linear_mm=0.1)})
    with pytest.raises(ValueError, match="canonical FDI"):
        MovementCaps(per_tooth_overrides={"UR1": AxisCaps(linear_mm=0.1)})

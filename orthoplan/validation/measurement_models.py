from __future__ import annotations

from pydantic import BaseModel, Field

MeasurementValue = float | int | bool | str


class MeasurementTruthResult(BaseModel):
    case_id: str
    passed: bool
    failures: list[str] = Field(default_factory=list)
    expected: dict[str, MeasurementValue] = Field(default_factory=dict)
    observed: dict[str, MeasurementValue] = Field(default_factory=dict)
    tolerances: dict[str, float] = Field(default_factory=dict)


def result(
    case_id: str,
    failures: list[str],
    *,
    expected: dict[str, MeasurementValue] | None = None,
    observed: dict[str, MeasurementValue] | None = None,
    tolerances: dict[str, float] | None = None,
) -> MeasurementTruthResult:
    return MeasurementTruthResult(
        case_id=case_id,
        passed=not failures,
        failures=failures,
        expected=expected or {},
        observed=observed or {},
        tolerances=tolerances or {},
    )


def close(
    actual: float,
    expected: float,
    tolerance: float,
    label: str,
    failures: list[str],
) -> None:
    if abs(actual - expected) > tolerance:
        failures.append(f"{label}: expected {expected}, got {actual}")

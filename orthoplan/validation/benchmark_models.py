from __future__ import annotations

from pydantic import BaseModel, Field


class BenchmarkMetric(BaseModel):
    name: str
    value: float
    unit: str = ""
    component: str
    case_id: str
    notes: str | None = None
    baseline_value: float | None = None
    delta_from_baseline: float | None = None


class BenchmarkCorpusScan(BaseModel):
    filename: str
    sha256: str
    arch: str
    units: str
    provenance: str
    vertex_count: int
    face_count: int


class BenchmarkCorpusCase(BaseModel):
    case_id: str
    source: str
    license: str
    phi_removed: bool
    consent_acknowledged: bool
    reviewed: bool
    notes: str
    scans: list[BenchmarkCorpusScan]


class BenchmarkReport(BaseModel):
    benchmark_id: str = "validation-benchmark-v2"
    baseline_id: str = "validation-benchmark-v1.2-baseline"
    caveat: str = (
        "Benchmark metrics are tracked numbers, not pass/fail clinical clearance. "
        "Synthetic fixtures and reviewed non-PHI scan corpus entries are reported "
        "with provenance so geometry changes show metric deltas over time."
    )
    metrics: list[BenchmarkMetric] = Field(default_factory=list)
    corpus_cases: list[BenchmarkCorpusCase] = Field(default_factory=list)

    def by_component(self) -> dict[str, list[BenchmarkMetric]]:
        grouped: dict[str, list[BenchmarkMetric]] = {}
        for metric in self.metrics:
            grouped.setdefault(metric.component, []).append(metric)
        return grouped

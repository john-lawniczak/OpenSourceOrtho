"""Heuristic auto-segmentation + the /api/segment payload contract."""

from __future__ import annotations

import math
from pathlib import Path

from orthoplan.evaluation.finding import FindingProvenance, lint_finding
from orthoplan.evaluation.finding import Finding
from orthoplan.mesh_workspace import resolve_mesh_path
from orthoplan.model.plan import TreatmentPlan
from orthoplan.segmentation.auto import build_advisory_findings, load_local_segmenter
from orthoplan.segmentation.heuristic import auto_segment_arch, default_arch_order
from orthoplan.segmentation.hybrid import hybrid_segment_arch_with_diagnostics
from orthoplan.segmentation.mesh_export import binary_stl_bytes
from orthoplan.segmentation_api import segment_payload

Vec3 = tuple[float, float, float]


def _arch_vertices(facets_per_tooth: int = 10) -> list[Vec3]:
    """Triangles laid out along a horseshoe in the occlusal (xy) plane."""

    teeth = len(default_arch_order("maxillary"))
    total = teeth * facets_per_tooth
    vertices: list[Vec3] = []
    for i in range(total):
        theta = math.pi * (i / (total - 1))  # 0..pi sweep around the arch
        cx, cy = 20.0 * math.cos(theta), 20.0 * math.sin(theta)
        vertices.extend(
            [
                (cx, cy, 0.0),
                (cx + 0.5, cy, 0.0),
                (cx, cy + 0.5, 0.3),
            ]
        )
    return vertices


def _write_arch_stl(path: Path) -> None:
    verts = _arch_vertices()
    triangles = [(verts[i], verts[i + 1], verts[i + 2]) for i in range(0, len(verts), 3)]
    path.write_bytes(binary_stl_bytes(triangles))


def test_auto_segment_arch_orders_teeth_and_scores_confidence() -> None:
    segments = auto_segment_arch(_arch_vertices(), arch="maxillary")
    order = list(default_arch_order("maxillary"))
    values = [s.tooth_value for s in segments]
    # Labels run in anatomical order along the arch; which physical end is first is
    # geometrically ambiguous (hence the manual-correction step), so accept either.
    assert values == order or values == list(reversed(order))
    assert all(0.0 <= s.confidence <= 0.8 for s in segments)
    assert all(s.triangles for s in segments)


def test_auto_segment_returns_empty_when_too_sparse() -> None:
    assert auto_segment_arch([(0.0, 0.0, 0.0)] * 9, arch="maxillary") == []


def test_load_local_segmenter_is_on_device_and_named() -> None:
    segmenter = load_local_segmenter()
    assert segmenter.name and segmenter.version
    assert "hybrid" in segmenter.name
    assert hasattr(segmenter, "segment")


def test_hybrid_segment_uses_surface_signal_boundaries() -> None:
    segments, diagnostics = hybrid_segment_arch_with_diagnostics(
        _arch_vertices(facets_per_tooth=12),
        arch="maxillary",
    )

    assert segments
    assert diagnostics.backend in {"pure-python", "open3d+pure-python"}
    assert len(diagnostics.boundary_buckets) == len(default_arch_order("maxillary")) - 1
    assert any(score > 0 for score in diagnostics.boundary_scores)


def test_advisory_findings_are_model_provenance_and_lint_clean() -> None:
    findings = build_advisory_findings(0.5)
    assert findings
    for finding in findings:
        assert finding.provenance == FindingProvenance.MODEL
        assert lint_finding(finding) is finding  # does not raise


def test_segment_payload_produces_reviewable_proposal(tmp_path: Path) -> None:
    ui_dir = tmp_path / "ui"
    ui_dir.mkdir()
    _write_arch_stl(ui_dir / "scan.stl")
    workspace = tmp_path / "ws"

    result = segment_payload(
        {"scans": [{"reference": "scan.stl", "arch": "maxillary"}]},
        ui_dir=ui_dir,
        workspace=workspace,
    )

    assert result["ok"] is True
    assert result["requires_review"] is True
    assert result["model"]["name"] == "hybrid-arch-graph-cut"
    assert result["model"]["backend"] in {"pure-python", "open3d+pure-python"}
    assert "graph cuts" in result["method"]
    assert result["teeth"]
    assert set(t["tooth"] for t in result["teeth"]) == set(default_arch_order("maxillary"))
    assert all(0.0 <= t["confidence"] <= 1.0 for t in result["teeth"])
    # Each proposed tooth mesh is written + resolvable from the local workspace.
    first_id = result["teeth"][0]["mesh_asset_id"]
    assert resolve_mesh_path(first_id, workspace=workspace) is not None


def test_segment_payload_fragment_merges_into_a_valid_plan(tmp_path: Path) -> None:
    ui_dir = tmp_path / "ui"
    ui_dir.mkdir()
    _write_arch_stl(ui_dir / "scan.stl")

    result = segment_payload(
        {"scans": [{"reference": "scan.stl", "arch": "maxillary"}]},
        ui_dir=ui_dir,
        workspace=tmp_path / "ws",
    )
    fragment = result["plan_fragment"]
    # The fragment is plan-ready: TreatmentPlan validation links every tooth mesh
    # to a declared mesh asset without raising.
    plan = TreatmentPlan.model_validate(
        {
            "id": "seg-merge-test",
            "mesh_assets": fragment["mesh_assets"],
            "tooth_meshes": fragment["tooth_meshes"],
        }
    )
    assert plan.tooth_meshes
    assert {m.id for m in plan.mesh_assets} >= {link.mesh_asset_id for link in plan.tooth_meshes}


def test_segment_payload_rejects_unresolvable_scan(tmp_path: Path) -> None:
    result = segment_payload(
        {"scans": [{"reference": "../../etc/passwd", "arch": "maxillary"}]},
        ui_dir=tmp_path,
        workspace=tmp_path,
    )
    assert result["ok"] is False
    assert result["errors"]


def test_segment_payload_requires_a_scan(tmp_path: Path) -> None:
    result = segment_payload({}, ui_dir=tmp_path, workspace=tmp_path)
    assert result["ok"] is False


def test_tooth_values_for_arch_drops_marked_gap() -> None:
    from orthoplan.segmentation.auto import tooth_values_for_arch

    full = default_arch_order("maxillary")
    labels = tooth_values_for_arch("maxillary", ["15"])
    assert labels == tuple(t for t in full if t != "15")
    assert len(labels) == len(full) - 1
    # Nothing marked, or a tooth from the other arch -> no override (None).
    assert tooth_values_for_arch("maxillary", []) is None
    assert tooth_values_for_arch("maxillary", ["38"]) is None


def test_segment_payload_anchors_labels_around_marked_gap(tmp_path: Path) -> None:
    ui_dir = tmp_path / "ui"
    ui_dir.mkdir()
    _write_arch_stl(ui_dir / "scan.stl")

    result = segment_payload(
        {"scans": [{"reference": "scan.stl", "arch": "maxillary"}], "missing_teeth": ["15"]},
        ui_dir=ui_dir,
        workspace=tmp_path / "ws",
    )
    assert result["ok"] is True
    teeth = [t["tooth"] for t in result["teeth"]]
    # The marked tooth is skipped and the arch is one tooth shorter than a full arch.
    assert "15" not in teeth
    assert len(teeth) == len(default_arch_order("maxillary")) - 1
    # A count-difference advisory is surfaced for review.
    assert any(
        "tooth count" in f["title"].lower() for f in result["advisory_findings"]
    )

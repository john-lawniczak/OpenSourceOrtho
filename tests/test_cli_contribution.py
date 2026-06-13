from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

from orthoplan import cli


def _write_binary_stl(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    triangle = (0, 0, 1, 0, 0, 0, 10, 0, 0, 0, 12, 0)
    path.write_bytes(
        b"\x00" * 80
        + struct.pack("<I", 1)
        + struct.pack("<12f", *triangle)
        + b"\x00\x00"
    )


def _case_bundle(tmp_path: Path) -> tuple[Path, list[Path], Path, Path]:
    case_dir = tmp_path / "spec-local"
    initial_upper = case_dir / "initial-upper.stl"
    initial_lower = case_dir / "initial-lower.stl"
    final_upper = case_dir / "final-upper.stl"
    progress_lower = case_dir / "progress-01-lower.stl"
    scans = [initial_upper, initial_lower, final_upper, progress_lower]
    for path in scans:
        _write_binary_stl(path)
    plan_summary = case_dir / "plan-summary.json"
    plan_summary.write_text(
        json.dumps(
            {
                "schema": "opensource-ortho-plan-summary-v1",
                "stage_count": 12,
                "wear_interval_days": 7,
                "arches_treated": ["upper", "lower"],
                "moved_teeth": ["11", "21"],
                "ipr_contacts": [{"between": ["11", "21"], "amount_mm": 0.2}],
                "refinement_count": 1,
            }
        ),
        encoding="utf-8",
    )
    outcome_notes = case_dir / "outcome-notes.md"
    outcome_notes.write_text("Tracked with one refinement. No identifiers.", encoding="utf-8")
    return case_dir, scans, plan_summary, outcome_notes


def _assert_manifest_labels(manifest_path: Path) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    by_file = {scan["filename"]: scan for scan in manifest["scans"]}
    assert by_file["initial-upper.stl"]["role"] == "initial"
    assert by_file["initial-upper.stl"]["arch"] == "maxillary"
    assert by_file["initial-lower.stl"]["arch"] == "mandibular"
    assert by_file["progress-01-lower.stl"]["role"] == "progress"
    assert by_file["progress-01-lower.stl"]["sequence_index"] == 1
    assert manifest["plan_summary"]["schema"] == "opensource-ortho-plan-summary-v1"
    assert manifest["plan_summary"]["stage_count"] == 12
    assert manifest["plan_summary_filename"] == "plan-summary.json"
    assert manifest["outcome_notes_filename"] == "outcome-notes.md"
    assert len(manifest["outcome_notes_sha256"]) == 64


def test_cli_register_contribution_labels_longitudinal_bundle(
    monkeypatch, capsys, tmp_path: Path
) -> None:
    case_dir, scans, plan_summary, outcome_notes = _case_bundle(tmp_path)
    manifest_path = case_dir / "manifest.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "orthoplan",
            "register-contribution",
            *[str(path) for path in scans],
            "--units",
            "mm",
            "--plan-summary",
            str(plan_summary),
            "--outcome-notes",
            str(outcome_notes),
            "--i-confirm-no-phi",
            "--out",
            str(manifest_path),
        ],
    )

    assert cli.main() == 0

    output = capsys.readouterr().out
    assert "Registered 4 scan(s) as spec-" in output
    _assert_manifest_labels(manifest_path)


def test_cli_register_contribution_rejects_phi_in_outcome_notes(
    monkeypatch, capsys, tmp_path: Path
) -> None:
    stl = tmp_path / "initial-upper.stl"
    _write_binary_stl(stl)
    notes = tmp_path / "outcome-notes.md"
    notes.write_text("Patient email is included here.", encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "orthoplan",
            "register-contribution",
            str(stl),
            "--outcome-notes",
            str(notes),
            "--i-confirm-no-phi",
        ],
    )

    assert cli.main() == 2
    captured = capsys.readouterr()
    assert "outcome notes contain patient-identifying" in captured.err

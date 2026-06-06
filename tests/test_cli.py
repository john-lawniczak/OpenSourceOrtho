from __future__ import annotations

import json
import sys
from pathlib import Path

from orthoplan import cli


def test_cli_new_plan_emits_json(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "argv", ["orthoplan", "new-plan", "--id", "cli-test"])

    assert cli.main() == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["id"] == "cli-test"
    assert payload["settings"]["timeline"]["wear_interval_days"] == 14


def test_cli_landmarks_template_emits_fillable_json(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "argv", ["orthoplan", "landmarks-template", "--arch", "upper"])

    assert cli.main() == 0

    payload = json.loads(capsys.readouterr().out)
    assert len(payload["landmarks"]) == 16  # full upper permanent dentition
    assert payload["landmarks"][0]["tooth"]["value"][0] in {"1", "2"}
    assert payload["landmarks"][0]["approximate"] is True


def test_cli_inspect_stl_handles_invalid_file_without_traceback(
    monkeypatch, capsys, tmp_path: Path
) -> None:
    path = tmp_path / "bad.stl"
    path.write_text("not a mesh", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["orthoplan", "inspect-stl", str(path)])

    assert cli.main() == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "inspect-stl error" in captured.err


def test_cli_plan_summary_handles_invalid_plan_without_traceback(
    monkeypatch, capsys, tmp_path: Path
) -> None:
    path = tmp_path / "bad-plan.json"
    path.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["orthoplan", "plan-summary", str(path)])

    assert cli.main() == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "plan-summary error" in captured.err


def test_cli_advise_handles_invalid_plan_without_traceback(
    monkeypatch, capsys, tmp_path: Path
) -> None:
    path = tmp_path / "bad-plan.json"
    path.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["orthoplan", "advise", str(path)])

    assert cli.main() == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "advise error" in captured.err


def test_cli_report_emits_handoff_report(monkeypatch, capsys, tmp_path: Path) -> None:
    plan_path = tmp_path / "plan.json"
    monkeypatch.setattr(
        sys,
        "argv",
        ["orthoplan", "new-plan", "--id", "report-plan", "--out", str(plan_path)],
    )
    assert cli.main() == 0
    capsys.readouterr()

    monkeypatch.setenv("REPORT_KEY", "secret")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "orthoplan",
            "report",
            str(plan_path),
            "--reviewer",
            "Dr. Test",
            "--signing-key-env",
            "REPORT_KEY",
        ],
    )
    assert cli.main() == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["schema"] == "orthoplan-report-v1"
    assert payload["plan"]["id"] == "report-plan"
    assert len(payload["evaluation_sha256"]) == 64
    assert len(payload["report_sha256"]) == 64
    assert payload["review"]["reviewer"] == "Dr. Test"
    assert payload["signature"]["algorithm"] == "HMAC-SHA256"


def test_cli_report_handles_invalid_plan_without_traceback(
    monkeypatch, capsys, tmp_path: Path
) -> None:
    path = tmp_path / "bad-plan.json"
    path.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["orthoplan", "report", str(path)])

    assert cli.main() == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "report error" in captured.err


def test_cli_acquisition_prints_ranked_advice(monkeypatch, capsys, tmp_path: Path) -> None:
    plan_path = tmp_path / "plan.json"
    monkeypatch.setattr(
        sys,
        "argv",
        ["orthoplan", "new-plan", "--id", "acq-plan", "--out", str(plan_path)],
    )
    assert cli.main() == 0
    capsys.readouterr()

    monkeypatch.setattr(sys, "argv", ["orthoplan", "acquisition", str(plan_path)])
    assert cli.main() == 0

    output = capsys.readouterr().out
    assert "Acquisition advisor for" in output
    assert "Baseline:" in output
    assert "Root data" in output


def test_cli_acquisition_json(monkeypatch, capsys, tmp_path: Path) -> None:
    plan_path = tmp_path / "plan.json"
    monkeypatch.setattr(
        sys,
        "argv",
        ["orthoplan", "new-plan", "--id", "acq-json", "--out", str(plan_path)],
    )
    assert cli.main() == 0
    capsys.readouterr()

    monkeypatch.setattr(sys, "argv", ["orthoplan", "acquisition", str(plan_path), "--json"])
    assert cli.main() == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["impacts"]


def test_cli_acquisition_handles_invalid_plan_without_traceback(
    monkeypatch, capsys, tmp_path: Path
) -> None:
    path = tmp_path / "bad-plan.json"
    path.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["orthoplan", "acquisition", str(path)])

    assert cli.main() == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "acquisition error" in captured.err


def test_cli_print_package_writes_files(monkeypatch, capsys, tmp_path: Path) -> None:
    plan_path = tmp_path / "plan.json"
    out_dir = tmp_path / "print"
    monkeypatch.setattr(
        sys,
        "argv",
        ["orthoplan", "new-plan", "--id", "print-cli", "--out", str(plan_path)],
    )
    assert cli.main() == 0
    capsys.readouterr()

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "orthoplan",
            "print-package",
            str(plan_path),
            "--out",
            str(out_dir),
            "--zip",
            "--email-draft",
        ],
    )
    assert cli.main() == 0

    output = capsys.readouterr().out
    assert "Wrote print package manifest" in output
    assert (out_dir / "print-cli-print-manifest.json").is_file()
    assert (out_dir / "print-cli-print-package.zip").is_file()
    assert (out_dir / "print-cli-print-package.eml").is_file()

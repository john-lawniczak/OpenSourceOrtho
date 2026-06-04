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

from __future__ import annotations

import json
import sys
from pathlib import Path

from orthoplan import cli
from orthoplan.watermark import CANARY_TOKEN, new_watermark, watermark_block


def _run(monkeypatch, args: list[str]) -> int:
    monkeypatch.setattr(sys, "argv", ["orthoplan", *args])
    return cli.main()


def test_verify_watermark_confirms_signed_stl(monkeypatch, tmp_path: Path) -> None:
    from orthoplan.print_stl import solid_stl

    mark = new_watermark()
    triangle = ((0.0, 0.0, 0.0), (10.0, 0.0, 0.0), (0.0, 10.0, 0.0))
    stl_path = tmp_path / "signed.stl"
    stl_path.write_text(solid_stl("part", [triangle], mark), encoding="utf-8")

    assert _run(monkeypatch, ["verify-watermark", str(stl_path)]) == 0


def test_verify_watermark_flags_missing_marker_on_plain_stl(monkeypatch, tmp_path: Path) -> None:
    from orthoplan.print_stl import solid_stl

    triangle = ((0.0, 0.0, 0.0), (10.0, 0.0, 0.0), (0.0, 10.0, 0.0))
    stl_path = tmp_path / "plain.stl"
    stl_path.write_text(solid_stl("part", [triangle]), encoding="utf-8")

    assert _run(monkeypatch, ["verify-watermark", str(stl_path)]) == 1


def test_verify_watermark_rejects_wrong_candidate_id(monkeypatch, tmp_path: Path) -> None:
    from orthoplan.print_stl import solid_stl

    mark = new_watermark()
    other = new_watermark()
    triangle = ((0.0, 0.0, 0.0), (10.0, 0.0, 0.0), (0.0, 10.0, 0.0))
    stl_path = tmp_path / "signed.stl"
    stl_path.write_text(solid_stl("part", [triangle], mark), encoding="utf-8")

    assert _run(monkeypatch, ["verify-watermark", str(stl_path), "--id", other.watermark_id]) == 1


def test_verify_watermark_reads_json_manifest_watermark_block(monkeypatch, tmp_path: Path) -> None:
    mark = new_watermark()
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({"watermark": watermark_block(mark)}), encoding="utf-8")

    assert _run(monkeypatch, ["verify-watermark", str(manifest_path)]) == 0


def test_verify_watermark_flags_json_without_watermark(monkeypatch, tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({"nothing": "here"}), encoding="utf-8")

    assert _run(monkeypatch, ["verify-watermark", str(manifest_path)]) == 1


def test_verify_watermark_scans_arbitrary_text_for_canary(monkeypatch, tmp_path: Path) -> None:
    hit = tmp_path / "output.txt"
    hit.write_text(f"model said: {CANARY_TOKEN}", encoding="utf-8")
    miss = tmp_path / "clean.txt"
    miss.write_text("nothing interesting here", encoding="utf-8")

    assert _run(monkeypatch, ["verify-watermark", str(hit)]) == 0
    assert _run(monkeypatch, ["verify-watermark", str(miss)]) == 1

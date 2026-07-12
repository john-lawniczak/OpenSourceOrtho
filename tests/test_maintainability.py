from pathlib import Path

from tools.check_maintainability import source_line_findings


def test_cross_language_budget_blocks_growth() -> None:
    relative = Path("ui/legacy.js")
    assert source_line_findings(relative, 12, {"ui/legacy.js": 11})[0].strict
    assert source_line_findings(relative, 11, {"ui/legacy.js": 11}) == []
    assert source_line_findings(Path("ui/new.js"), 501, {})[0].strict


def test_maintainability_baseline_covers_current_cross_language_hotspots() -> None:
    from tools.check_maintainability import first_party_source_files, load_line_baseline, line_count

    baseline = load_line_baseline()
    oversized = [path for path in first_party_source_files() if line_count(path) > 500]
    assert oversized
    for path in oversized:
        relative = path.relative_to(Path(__file__).resolve().parents[1]).as_posix()
        assert relative in baseline
        assert line_count(path) <= baseline[relative]

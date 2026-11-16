"""Local review persistence, capture alternatives and edit-session recovery."""

import json
import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect, sync_playwright  # noqa: E402
from test_chat_workspace import server_url  # noqa: E402,F401
from test_tooth_goals import open_supplied_sample  # noqa: E402
from orthoplan.io.stl_export import binary_stl_bytes  # noqa: E402


def test_multiple_captures_save_restore_without_fit(server_url, tmp_path):  # noqa: F811 - pytest fixture
    scans = []
    for name, height in [("first", 1), ("cleaner", 2), ("later", 3)]:
        path = tmp_path / f"{name}.stl"
        path.write_bytes(binary_stl_bytes([[(0, 0, 0), (1, 0, 0), (0, height, 0)]]))
        scans.append(path)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            page.goto(server_url + "/progress.html")
            page.locator("#scan0").set_input_files(scans[:2])
            expect(page.locator("#activeCapture0 option")).to_have_count(3)
            page.locator("#activeCapture0").select_option(label="cleaner.stl")
            page.locator("#model0").fill("Cast A")
            page.locator("#damage0").fill("First capture has a chip")
            page.locator("#acquired0").fill("2026-11-10")
            page.locator("#scan1").set_input_files(scans[2])
            expect(page.locator("#activeCapture1 option")).to_have_count(2)
            page.locator("#caseName").fill("Alternative captures")
            page.locator("#saveCase").click()
            expect(page.locator("#caseStatus")).to_contain_text("Case saved locally")
            page.reload()
            page.locator("#openCase").click()
            expect(page.locator("#caseStatus")).to_contain_text("cleaner.stl → later.stl")
            expect(page.locator("#activeCapture0 option")).to_have_count(3)
            expect(page.locator("#model0")).to_have_value("Cast A")
            expect(page.locator("#damage0")).to_have_value("First capture has a chip")
            expect(page.locator("#acquired0")).to_have_value("2026-11-10")
            expect(page.locator("#unitsConfirmed")).not_to_be_checked()
            expect(page.locator("#caseWeeks button")).to_have_count(0)
            with page.expect_download() as event:
                page.locator("#backupCase").click()
            backup = tmp_path / "captures.orthocase"
            event.value.save_as(backup)
            page.locator("#restoreCase").set_input_files(backup)
            expect(page.locator("#caseStatus")).to_contain_text("Backup verified")
            page.locator("#openCase").click()
            expect(page.locator("#model0")).to_have_value("Cast A")
            page.locator("#activeCapture0").select_option(label="first.stl")
            expect(page.locator("#model0")).to_have_value("")
            page.locator("#activeCapture0").select_option(label="cleaner.stl")
            expect(page.locator("#model0")).to_have_value("Cast A")
            assert not errors
            page.screenshot(path=str(tmp_path / "captures.png"), full_page=True)
        finally:
            browser.close()


def test_review_redo_and_recovery_after_reload(server_url, tmp_path):  # noqa: F811 - pytest fixture
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1400})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            page.goto(server_url)
            open_supplied_sample(page)
            page.locator('.viewer-tooth-numbers [data-select-tooth="11"]').click()
            page.locator("#toothReviewDetails summary").click()
            page.locator("#toothReviewer").fill("Local contributor")
            page.locator("#toothReviewNotes").fill("Checked boundary against the scan")
            page.locator("#reviewSelectedRegion").check()
            expect(page.locator("#toothReviewStatus")).to_contain_text("Contributor review saved")
            page.locator('#toothWorkspace [data-manual-nudge="x+"]').first.click()
            expect(page.locator("#applyGoalPreview")).to_be_enabled(timeout=60000)
            page.locator("#applyGoalPreview").click()
            applied = json.loads(page.locator("#planJson").input_value())
            page.locator("#guidedEditUndo").click()
            undone = json.loads(page.locator("#planJson").input_value())
            assert undone["stages"] != applied["stages"]
            page.locator("#guidedEditRedo").click()
            assert (
                json.loads(page.locator("#planJson").input_value())["stages"] == applied["stages"]
            )
            page.locator("#editSessionDetails summary").click()
            expect(page.locator("#editSessionStatus")).to_contain_text("saved in this browser")
            page.reload()
            open_supplied_sample(page)
            page.locator('.viewer-tooth-numbers [data-select-tooth="11"]').click()
            expect(page.locator("#reviewSelectedRegion")).to_be_checked()
            page.locator("#toothReviewDetails summary").click()
            expect(page.locator("#toothReviewNotes")).to_have_value(
                "Checked boundary against the scan"
            )
            page.locator("#editSessionDetails summary").click()
            page.once("dialog", lambda dialog: dialog.accept())
            page.locator("#restoreEditSession").click()
            expect(page.locator("#editSessionStatus")).to_contain_text("Restored applied edits")
            assert (
                json.loads(page.locator("#planJson").input_value())["stages"] == applied["stages"]
            )
            expect(page.locator("#guidedEditUndo")).to_be_enabled()
            assert not errors
            page.locator("#toothWorkspace").screenshot(path=str(tmp_path / "recovered-edits.png"))
            page.locator("#toothReviewUncertain").check()
            page.locator("#saveToothReview").click()
            expect(page.locator("#saveToothReview")).to_be_enabled()
            expect(page.locator("#reviewSelectedRegion")).not_to_be_checked()
            expect(page.locator('#toothWorkspace [data-manual-nudge="x+"]')).to_be_disabled()
            page.locator("#themeToggle").click()
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.locator("#toothWorkspace").screenshot(
                path=str(tmp_path / "review-dark-mobile.png")
            )

        finally:
            browser.close()


def test_saved_label_refit_and_agreement_report(server_url, tmp_path):  # noqa: F811 - pytest fixture
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            page.goto(server_url)
            page.locator("#sampleLaunch").click()
            page.locator('[data-comparison-arch="upper"]').click()
            expect(page.locator("#sampleComparison")).to_have_attribute(
                "data-ready", "true", timeout=30000
            )
            page.locator("#comparisonDiagnostics > summary").click()
            page.get_by_text("Saved-label experiments", exact=True).click()
            page.locator('[data-research="build"]').click()
            status = page.locator('[data-research="status"]')
            expect(status).to_contain_text("Saved fit:", timeout=90000)
            expect(page.locator("#sampleComparison")).to_have_attribute(
                "data-ready", "true", timeout=30000
            )
            page.locator('[data-comparison-week="3"]').click()
            expect(page.locator("#comparisonVisit")).to_contain_text("SIMULATED ESTIMATE")
            expect(page.locator('[data-research="fit"] option')).to_have_count(2)
            with page.expect_download() as event:
                page.locator('[data-research="download"]').click()
            path = tmp_path / "fit.json"
            event.value.save_as(path)
            fit = json.loads(path.read_text())
            assert fit["summary"]["regions"] > 0
            assert fit["summary"]["motion_accuracy"] is None
            assert len(fit["reference_snapshots"]) == 2
            assert fit["comparison"]["original"]["regions"] > 0
            page.locator('[data-research="benchmark"]').click()
            expect(status).to_contain_text("Saved contributor-agreement report", timeout=60000)
            with page.expect_download() as event:
                page.locator('[data-research="download"]').click()
            path = tmp_path / "agreement.json"
            event.value.save_as(path)
            report = json.loads(path.read_text())
            assert report["independent_accuracy"] is None
            assert report["reports"][0]["face_count"] > 0
            page.locator('[data-research="fit"]').select_option("")
            expect(status).to_contain_text("Showing the bundled fit")
            expect(page.locator("#sampleComparison")).to_have_attribute(
                "data-ready", "true", timeout=30000
            )
            page.locator("#comparisonDiagnostics").screenshot(
                path=str(tmp_path / "fit-reports.png")
            )
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            assert not errors
        finally:
            browser.close()

"""Exercise uploads, real fitting, frame selection, correction export and saved reload."""

import base64
import hashlib
import json
import pytest

pytest.importorskip("playwright.sync_api")
np = pytest.importorskip("numpy")
from playwright.sync_api import expect, sync_playwright  # noqa: E402
from test_chat_workspace import server_url  # noqa: E402,F401
from orthoplan.io.stl_export import binary_stl_bytes as binary_mesh  # noqa: E402


def test_upload_fit_correct_and_restore(server_url, tmp_path):  # noqa: F811
    triangles = np.random.default_rng(20).normal(size=(200, 3, 3))
    raw = binary_mesh(triangles)
    scan = tmp_path / "first.stl"
    scan.write_bytes(raw)
    correction = tmp_path / "correction.json"
    correction.write_text(
        json.dumps(
            dict(
                schema="ortho-region-corrections-v1",
                source_sha256=hashlib.sha256(raw).hexdigest(),
                arch="upper",
                face_count=200,
                labels_base64=base64.b64encode(bytes([11] * 200)).decode(),
            )
        )
    )
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1200, "height": 1000})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            page.goto(server_url + "/progress.html")
            for i in range(2):
                page.locator(f"#scan{i}").set_input_files(scan)
                page.locator(f"#correction{i}").set_input_files(correction)
            page.locator("#unitsConfirmed").check()
            page.locator("#fitVisits").click()
            expect(page.locator("#caseStatus")).to_contain_text("Fit complete", timeout=30000)
            page.get_by_role("button", name="Week 4", exact=True).click()
            expect(page.locator("#frameLabel")).to_contain_text("SIMULATED ESTIMATE")
            expect(page.get_by_role("button", name="Week 4", exact=True)).to_have_attribute(
                "aria-current", "step"
            )
            with page.expect_download() as event:
                page.locator("#exportRegions0").click()
            event.value.save_as(tmp_path / "draft.json")
            assert (
                json.loads((tmp_path / "draft.json").read_text())["source_sha256"]
                == hashlib.sha256(raw).hexdigest()
            )
            page.locator("#caseName").fill("Verified local case")
            page.locator("#saveCase").click()
            expect(page.locator("#caseStatus")).to_contain_text("Case saved locally")
            page.reload()
            expect(page.locator("#savedCases")).to_have_value("Verified local case")
            page.locator("#openCase").click()
            expect(page.locator("#caseStatus")).to_contain_text("Opened Verified local case")
            expect(page.locator("#caseWeeks button")).to_have_count(7)
            page.locator("#referenceTeeth").fill("11")
            page.locator("#referenceTeeth").press("Tab")
            page.locator("#fitVisits").click()
            expect(page.locator("#caseStatus")).to_contain_text("Fit complete", timeout=30000)
            assert not errors
            page.screenshot(path=str(tmp_path / "two-visit-workspace.png"))
        finally:
            browser.close()

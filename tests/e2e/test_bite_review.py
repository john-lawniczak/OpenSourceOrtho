import json
import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect, sync_playwright  # noqa: E402
from test_chat_workspace import server_url  # noqa: E402,F401
from orthoplan.io.stl_export import binary_stl_bytes  # noqa: E402


def test_bite_review_template_and_explicit_identity_frame(server_url, tmp_path):  # noqa: F811
    upper = tmp_path / "upper.stl"
    lower = tmp_path / "lower.stl"
    face = ((0, 0, 0), (1, 0, 0), (0, 1, 0))
    lower.write_bytes(binary_stl_bytes([face]))
    upper.write_bytes(binary_stl_bytes([tuple((x, y, z + 1) for x, y, z in face)]))
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            page.goto(server_url + "/bite-review.html")
            page.locator("#biteUpper").set_input_files(upper)
            page.locator("#biteLower").set_input_files(lower)
            page.locator("#biteUnits").check()
            page.locator("#inspectBite").click()
            expect(page.locator("#biteStatus")).to_contain_text("geometric-inference")
            with page.expect_download() as event:
                page.locator("#biteTemplate").click()
            record = tmp_path / "bite.json"
            event.value.save_as(record)
            data = json.loads(record.read_text())
            assert data["accepted"] is False
            data.update(
                accepted=True,
                reviewer="Fixture reviewer",
                reference_description="Known synthetic shared frame",
            )
            record.write_text(json.dumps(data))
            page.locator("#biteRecord").set_input_files(record)
            page.locator("#inspectBite").click()
            expect(page.locator("#biteStatus")).to_contain_text("reviewed-transform")
            expect(page.locator("#showBiteProposal")).to_be_checked()
            assert not errors
        finally:
            browser.close()

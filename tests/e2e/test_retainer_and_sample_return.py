"""Separate reference preparation and sample navigation preserve source state."""
import hashlib
import json
import io

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect, sync_playwright  # noqa: E402
from PIL import Image  # noqa: E402
import numpy as np  # noqa: E402
from test_chat_workspace import server_url  # noqa: E402,F401
from test_boundary_intake import surface  # noqa: E402


def assert_camera_unchanged(before, canvas, tmp_path):
    # Exclude the HTML zoom overlay, whose focus moves to step buttons.
    old = np.array(Image.open(io.BytesIO(before)))
    new = np.array(Image.open(io.BytesIO(canvas.screenshot(path=str(tmp_path / "history-after.png")))))
    assert old.shape == new.shape
    assert np.any(old[:, :-80] != new[:, :-80], axis=2).mean() < .001


def test_history_survives_guided_steps_and_retainer_preparation(server_url, tmp_path):  # noqa: F811
    stl = surface(tmp_path)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            page.goto(server_url)
            page.locator("#sampleLaunch").click()
            expect(page.locator("#sampleComparison")).to_have_attribute("data-ready", "true", timeout=60000)
            page.locator('[data-comparison-week="7"]').click()
            page.locator("#highlightEstimatedWeeks").uncheck()
            page.locator("#comparisonZoomIn").click()
            original_canvas = page.locator("#comparisonCanvas canvas").element_handle()
            before = original_canvas.screenshot(path=str(tmp_path / "history-before.png"))
            for step in ["details", "review", "preview"]:
                page.locator(f'[data-gstep-nav="{step}"] button').click()
                expect(page.locator('button[data-sample-view="simulation"]')).to_have_attribute("aria-pressed", "true")
                page.locator('[data-gstep-nav="plan"] button').click()
                expect(page.locator('button[data-sample-view="observed"]')).to_have_attribute("aria-pressed", "true")
                expect(page.locator("#sampleComparison")).to_have_attribute("data-week", "7")
                expect(page.locator("#highlightEstimatedWeeks")).not_to_be_checked()
                assert original_canvas.evaluate("el => el === document.querySelector('#comparisonCanvas canvas')")
            assert_camera_unchanged(before, original_canvas, tmp_path)
            for step in ["review", "preview", "print"]:
                page.locator(f'[data-gstep-nav="{step}"] button').click()
                page.locator('button[data-sample-view="observed"]').click()
                expect(page.locator("#sampleComparison")).to_be_visible()
                expect(page.locator("#sampleComparison")).to_have_attribute("data-week", "7")
            page.locator("#createRetainer").click()
            flow = page.frame_locator('iframe[title="Retainer reference preparation"]')
            flow.locator("#retainerFile").set_input_files(stl)
            flow.locator("#retainerArch").select_option("lower")
            flow.locator("#retainerCurrent").check()
            flow.locator("#retainerPrepare").click()
            expect(flow.locator("#retainerStatus")).to_contain_text("Reference ready")
            with page.expect_download() as model_download:
                flow.locator("#retainerDownload").click()
            model_path = tmp_path / "reference.stl"
            model_download.value.save_as(model_path)
            assert model_path.read_bytes() == stl.read_bytes()
            with page.expect_download() as record_download:
                flow.locator("#retainerRecord").click()
            record_path = tmp_path / "preparation.json"
            record_download.value.save_as(record_path)
            record = json.loads(record_path.read_text())
            assert record["reference_model"]["sha256"] == hashlib.sha256(stl.read_bytes()).hexdigest()
            assert not record["wearable_output"] and record["proposed_movements"] == []
            page.screenshot(path=str(tmp_path / "retainer-first-step.png"), full_page=True)
            flow.locator("#retainerUnits").select_option("mm")
            expect(flow.locator("#retainerResult")).to_be_hidden()
            page.locator("#retainerWorkspaceBack").click()
            expect(page.locator("#sampleComparison")).to_be_visible()
            expect(page.locator("#sampleComparison")).to_have_attribute("data-week", "7")
            assert not errors
        finally:
            browser.close()

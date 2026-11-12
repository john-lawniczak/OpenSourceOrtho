"""Brush cursor dimensions and tooth-centered camera behavior are visible."""
import io

import pytest

pytest.importorskip("playwright.sync_api")
from PIL import Image  # noqa: E402
from playwright.sync_api import expect, sync_playwright  # noqa: E402
from test_chat_workspace import server_url  # noqa: E402,F401
from test_boundary_intake import surface  # noqa: E402


def amber_width(png):
    image = Image.open(io.BytesIO(png)).convert("RGB")
    points = [(x, y) for y in range(image.height) for x in range(image.width)
              if (lambda c: c[0] > 200 and 100 < c[1] < 230 and c[2] < 110)(image.getpixel((x, y)))]
    assert points, "Brush ring should be visible on the unlabeled surface"
    return max(x for x, _ in points) - min(x for x, _ in points)


def test_stationary_brush_updates_from_keys_buttons_and_input(server_url, tmp_path):  # noqa: F811
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        try:
            page.goto(server_url + "/region-review.html")
            page.locator("#reviewScan").set_input_files(surface(tmp_path))
            expect(page.locator("#reviewSource")).to_contain_text("lower_test.stl")
            page.get_by_role("button", name="Paint tooth", exact=True).click()
            canvas = page.locator("#regionCanvas canvas")
            canvas.hover()
            small = amber_width(canvas.screenshot())
            for _ in range(10):
                page.keyboard.press("BracketRight")
            expect(page.locator("#reviewRadius")).to_have_value("2.0")
            large = amber_width(canvas.screenshot(path=str(tmp_path / "brush-radius-2.png")))
            assert large > small * 1.7
            # Numeric input and buttons update the ring at its last hover point.
            page.locator("#reviewRadius").fill("4")
            assert page.locator("#reviewRadius").bounding_box()["width"] <= 100
            assert amber_width(canvas.screenshot()) > large * 1.7
            page.locator("#reviewBrushSmaller").click()
            expect(page.locator("#reviewRadius")).to_have_value("3.9")
            expect(page.locator("#reviewStatus")).to_contain_text("0 correction operations")
            viewport = page.locator(".review-viewport").bounding_box()
            zoom = page.locator("#reviewZoomIn").bounding_box()
            assert viewport["x"] < zoom["x"] < viewport["x"] + viewport["width"]
            assert viewport["y"] < zoom["y"] < viewport["y"] + 60
        finally:
            browser.close()


def test_default_view_restores_full_upper_after_focus_roll_and_zoom(server_url, tmp_path, monkeypatch):  # noqa: F811
    from test_boundary_intake import export

    monkeypatch.setenv("ORTHOPLAN_REGION_CORRECTIONS", str(tmp_path / "labels"))
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        try:
            page.goto(server_url + "/region-review.html?baseline=upper")
            expect(page.locator("#reviewSource")).to_contain_text("initial-upper.stl", timeout=30000)
            default = page.get_by_role("button", name="Default view", exact=True)
            default.click()
            canvas = page.locator("#regionCanvas canvas")
            before_view = canvas.screenshot(path=str(tmp_path / "upper-default-view.png"))
            before_labels = export(page, tmp_path, "before-default.json")
            page.locator("#reviewFocus").click()
            page.locator('[data-scan-view="roll-left"]').click()
            page.locator("#reviewZoomIn").click()
            assert canvas.screenshot() != before_view
            default.click()
            assert canvas.screenshot() == before_view
            assert export(page, tmp_path, "after-default.json") == before_labels
            expect(page.locator("#reviewStatus")).to_contain_text("0 correction operations")
        finally:
            browser.close()


def test_focused_view_presets_keep_marker_centered(server_url, tmp_path, monkeypatch):  # noqa: F811
    monkeypatch.setenv("ORTHOPLAN_REGION_CORRECTIONS", str(tmp_path / "labels"))
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        try:
            page.goto(server_url + "/region-review.html?baseline=upper")
            expect(page.locator("#reviewSource")).to_contain_text("initial-upper.stl", timeout=30000)
            page.locator('[data-tooth="21"]').click()
            page.locator("#reviewShowLabel").check()
            page.locator("#reviewFocus").click()
            for command in ["flip", "above", "side", "face"]:
                page.locator(f'[data-scan-view="{command}"]').click()
                marker = page.locator("#reviewSelectionMarker")
                expect(marker).to_be_visible()
                left = marker.evaluate("el => parseFloat(el.style.left)")
                top = marker.evaluate("el => parseFloat(el.style.top)")
                bounds = page.locator("#regionCanvas").bounding_box()
                assert abs(left - bounds["width"] / 2) < 3
                assert abs(top - bounds["height"] / 2) < 3
            expect(page.locator("#reviewStatus")).to_contain_text("0 correction operations")
            page.screenshot(path=str(tmp_path / "compact-focused-editor.png"), full_page=True)
        finally:
            browser.close()


def test_pan_moves_mouth_without_painting_and_survives_presets(server_url, tmp_path, monkeypatch):  # noqa: F811
    monkeypatch.setenv("ORTHOPLAN_REGION_CORRECTIONS", str(tmp_path / "labels"))
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        try:
            page.goto(server_url + "/region-review.html?baseline=upper")
            expect(page.locator("#reviewSource")).to_contain_text("initial-upper.stl", timeout=30000)
            page.locator('[data-tooth="21"]').click()
            page.locator("#reviewShowLabel").check()
            page.locator("#reviewFocus").click()
            page.get_by_role("button", name="✥ Pan", exact=True).click()
            page.locator('[data-scan-view="flip"]').click()
            marker = page.locator("#reviewSelectionMarker")
            before = marker.evaluate("e => [parseFloat(e.style.left), parseFloat(e.style.top)]")
            canvas = page.locator("#regionCanvas canvas").bounding_box()
            x, y = canvas["x"] + canvas["width"] / 2, canvas["y"] + canvas["height"] / 2
            page.mouse.move(x, y)
            page.mouse.down()
            page.mouse.move(x + 100, y + 60, steps=8)
            page.mouse.up()
            after = marker.evaluate("e => [parseFloat(e.style.left), parseFloat(e.style.top)]")
            assert abs(after[0] - before[0] - 100) < 3
            assert abs(after[1] - before[1] - 60) < 3
            expect(page.locator("#reviewStatus")).to_contain_text("0 correction operations")
            page.screenshot(path=str(tmp_path / "pan-controls.png"), full_page=True)
        finally:
            browser.close()


def test_double_click_unlabeled_surface_centers_and_zooms(server_url, tmp_path):  # noqa: F811
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        try:
            page.goto(server_url + "/region-review.html")
            page.locator("#reviewScan").set_input_files(surface(tmp_path))
            expect(page.locator("#reviewSource")).to_contain_text("lower_test.stl")
            canvas = page.locator("#regionCanvas canvas")
            before = canvas.screenshot()
            canvas.dblclick()
            assert canvas.screenshot() != before
            expect(page.locator("#reviewStatus")).to_contain_text("unlabeled")
            page.locator('[data-scan-view="flip"]').click()
            page.get_by_role("button", name="✥ Pan", exact=True).click()
            page.locator('[data-scan-view="fit"]').click()
            expect(page.get_by_role("button", name="✥ Pan", exact=True)).to_have_attribute("aria-pressed", "true")
        finally:
            browser.close()

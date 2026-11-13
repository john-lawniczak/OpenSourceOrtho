"""Saved painted regions, explicit numbering, and camera-only navigation."""
import json

import pytest
pytest.importorskip('playwright.sync_api')
from playwright.sync_api import expect, sync_playwright  # noqa: E402
from test_chat_workspace import server_url  # noqa: E402,F401


def test_week_seven_number_selection_and_navigation(server_url, tmp_path):  # noqa: F811
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 1500})
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        try:
            page.goto(server_url)
            page.locator('#sampleLaunch').click()
            page.locator('[data-gstep-nav="details"]').click()
            expect(page.locator('#sampleReloadPainting')).to_be_enabled(timeout=90000)
            teeth = page.locator('#guidedTeeth [data-select-tooth]')
            expect(teeth).to_have_count(28)
            plan = json.loads(page.locator('#planJson').input_value())
            assert all(not item['reviewed'] for item in plan['tooth_meshes'])
            for quadrant in range(1, 5):
                for position in range(1, 8):
                    tooth = str(quadrant * 10 + position)
                    page.locator('#toothNumberInput').fill(tooth)
                    page.locator('#toothNumberForm button').click()
                    expect(page.locator(f'#guidedTeeth [data-select-tooth="{tooth}"]')).to_have_attribute('aria-pressed', 'true')
            page.locator('#toothNumberSystem').select_option('US')
            page.locator('#toothNumberInput').fill('8')
            page.locator('#toothNumberForm button').click()
            selected = page.locator('#guidedTeeth [data-select-tooth="11"]')
            expect(selected).to_have_attribute('aria-pressed', 'true')
            page.locator('#toothNumberInput').fill('1')
            page.locator('#toothNumberForm button').click()
            expect(page.locator('#toothNumberStatus')).to_contain_text('No painted region')
            expect(selected).to_have_attribute('aria-pressed', 'true')
            page.wait_for_load_state('networkidle')
            page.locator('#viewer3d').screenshot(path=str(tmp_path/'week7-front.png'))
            page.locator('[data-viewer-focus]').click()
            page.locator('[data-viewer-drag="pan"]').click()
            box = page.locator('#viewer3d canvas').bounding_box()
            x, y = box['x'] + box['width']/2, box['y'] + box['height']/2
            page.mouse.move(x, y)
            page.mouse.down()
            page.mouse.move(x+100, y+30, steps=10)
            page.mouse.up()
            expect(selected).to_have_attribute('aria-pressed', 'true')
            page.locator('.scan-view-controls:visible [data-scan-view="face"]').click()
            expect(page.locator('[data-viewer-drag="pan"]')).to_have_attribute('aria-pressed', 'true')
            assert json.loads(page.locator('#planJson').input_value()) == plan
            page.locator('#sampleReloadPainting').click()
            expect(page.locator('#sampleReloadPainting')).to_be_enabled(timeout=90000)
            expect(teeth).to_have_count(28)
            assert not errors
        finally:
            browser.close()

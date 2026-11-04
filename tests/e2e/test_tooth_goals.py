"""The sample exercises the same reviewed-tooth editing path as an upload."""
import json
import base64

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect, sync_playwright  # noqa: E402
from test_chat_workspace import server_url  # noqa: E402,F401


def amber_crown_point(page):
    png = page.locator('#viewer3d canvas').screenshot()
    return page.evaluate("""async data => {
      const image = new Image(); image.src = data; await image.decode();
      const canvas = document.createElement('canvas'); canvas.width = image.width; canvas.height = image.height;
      const ctx = canvas.getContext('2d'); ctx.drawImage(image, 0, 0);
      const pixels = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
      let run = 0, longest = 0, point = null;
      for (let i = 0; i < pixels.length; i += 4) {
        const [r, g, b] = pixels.slice(i, i + 3);
        if (r > g + 20 && g > b + 25) {
          run++;
          if (run > longest) { longest = run; point = {x: (i / 4) % canvas.width - Math.floor(run / 2), y: Math.floor(i / 4 / canvas.width)}; }
        } else run = 0;
      }
      return point;
    }""", 'data:image/png;base64,' + base64.b64encode(png).decode())


def open_supplied_sample(page):
    page.locator('#sampleLaunch').click()
    expect(page.locator('#simpleStlFile')).to_be_disabled()
    expect(page.locator('#sampleBanner')).to_contain_text('STL')


def test_reviewed_scan_tooth_preview_apply_discard_and_undo(server_url, tmp_path):
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        try:
            page.goto(server_url, wait_until='networkidle')
            open_supplied_sample(page)
            tooth = page.locator('#guidedTeeth [data-select-tooth="11"]')
            expect(tooth).to_be_visible(timeout=90000)
            tooth.click()
            expect(tooth).to_have_attribute('aria-pressed', 'true')
            before = json.loads(page.locator('#planJson').input_value())
            (tmp_path / "before.json").write_text(json.dumps(before))
            assert not before['fixed_teeth']
            viewer = page.locator('#viewer3d')
            assert tooth.bounding_box()['y'] > viewer.bounding_box()['y']
            point = amber_crown_point(page)
            assert point is not None, 'Selected real crown must render in amber'
            page.locator('#guidedClearSelection').click()
            page.locator('#viewer3d canvas').click(position=point)
            expect(tooth).to_have_attribute('aria-pressed', 'true')
            page.locator('[data-manual-nudge="x+"]').first.click()
            expect(page.locator('#applyGoalPreview')).to_be_enabled(timeout=60000)
            assert json.loads(page.locator('#planJson').input_value()) == before
            expect(page.locator('#goalPreviewText')).to_contain_text('Tooth 11')
            page.locator('#discardGoalPreview').click()
            expect(page.locator('#goalPreviewPanel')).not_to_be_visible()
            assert json.loads(page.locator('#planJson').input_value()) == before
            page.locator('#askSelectedTooth').click()
            expect(page.locator('#chatEditMode')).to_be_checked()
            page.locator('#chatInput').fill('move 0.2 mm right')
            page.locator('#sendChat').click()
            expect(page.locator('#applyGoalPreview')).to_be_enabled(timeout=60000)
            expect(page.locator('.chat-message.user').last).to_contain_text('move 0.2 mm right')
            expect(page.locator('.chat-message.assistant').last).to_contain_text('Apply or Discard')
            page.locator('#toggleChatPanel').click()
            page.locator('#stageSlider').fill('0')
            page.locator('#applyGoalPreview').click()
            after = json.loads(page.locator('#planJson').input_value())
            def total(plan):
                return sum(d['translate_x_mm'] for s in plan['stages'] for d in s['deltas'] if d['tooth']['value'] == '11')
            assert total(after) == pytest.approx(total(before) + .2)
            assert any(d['source'] == 'model' for s in after['stages'] for d in s['deltas'] if d['tooth']['value'] == '11')
            page.locator('#guidedEditUndo').click()
            assert json.loads(page.locator('#planJson').input_value()) == before
            page.locator('#holdSelectedTooth').check()
            expect(page.locator('[data-manual-nudge="x+"]').first).to_be_disabled()
            assert json.loads(page.locator('#planJson').input_value())['fixed_teeth'][0]['tooth']['value'] == '11'
            page.locator('#holdSelectedTooth').uncheck()
            page.locator('#viewerBlock').screenshot(path=str(tmp_path/'tooth-workspace.png'))
            page.get_by_role('button', name='Open the imaging and photos guide').click()
            expect(page.locator('#imagingViewerHost #viewer3d canvas')).to_be_visible()
            expect(page.locator('#imagingScanList')).to_contain_text('initial-upper.stl')
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.locator('#viewerBlock').evaluate('el => el.scrollWidth <= el.clientWidth')
            assert not errors
        finally:
            browser.close()

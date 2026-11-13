"""Guided navigation and shared controls stay usable across all scan steps."""
import pytest
pytest.importorskip('playwright.sync_api')
from playwright.sync_api import expect, sync_playwright  # noqa: E402
from test_chat_workspace import server_url  # noqa: E402,F401


def test_header_profile_and_sample_number_controls(server_url, tmp_path):  # noqa: F811
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 1100})
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        try:
            page.goto(server_url, wait_until='networkidle')
            expect(page.locator('#teethProfile')).to_have_attribute('aria-pressed', 'true')
            page.locator('#teethProfile').click()
            expect(page.locator('#teethProfile')).to_have_attribute('aria-pressed', 'true')
            expect(page.locator('#teethProfileStatus')).not_to_contain_text('Start with')
            page.locator('#topbarAskAI').click()
            expect(page.locator('#chatInput')).to_be_focused()
            expect(page.locator('#topbarAskAI')).to_have_attribute('aria-expanded', 'true')
            page.locator('#toggleChatPanel').click()
            page.locator('#sampleLaunch').click()
            expect(page.locator('#guidedRail')).to_be_visible()
            expect(page.locator('#teethProfile')).to_have_attribute('aria-pressed', 'false')
            expect(page.locator('#wearInterval')).to_have_value('7')
            page.locator('#topbarAskAI').click()
            expect(page.locator('#chatInput')).to_be_visible()
            page.locator('#toggleChatPanel').click()
            expect(page.locator('#guidedNext')).to_be_visible()
            page.locator('#guidedNext').click()
            page.locator('[data-gstep-nav="details"]').click()
            expect(page.locator('#sampleReloadPainting')).to_be_enabled(timeout=90000)
            # Section 2 preserves its overview choice; explicitly choose tooth controls.
            page.locator('button[data-sample-view="simulation"]').click()
            for step in ['plan', 'details', 'preview']:
                page.locator(f'[data-gstep-nav="{step}"]').click()
                numbers = page.locator('.viewer-tooth-numbers')
                expect(numbers).to_be_visible()
                numbers.locator('[data-select-tooth="31"]').click()
                expect(page.locator('#guidedTeeth [data-select-tooth="31"]')).to_have_attribute('aria-pressed', 'true')
                page.locator('#toothLabelToggle').click()
                expect(numbers).to_be_hidden()
                page.locator('#toothLabelToggle').click()
                expect(numbers).to_be_visible()
            page.locator('#viewer3d').screenshot(path=str(tmp_path/'numbered-preview.png'))
            page.locator('#themeToggle').click()
            page.set_viewport_size({'width': 390, 'height': 844})
            page.locator('.viewer3d-wrap').screenshot(path=str(tmp_path/'numbered-mobile.png'))
            overflow = page.locator('#viewerBlock').evaluate('el => [...el.querySelectorAll("*")].filter(x => x.getBoundingClientRect().right > el.getBoundingClientRect().right + 1).map(x => [x.tagName,x.id,x.className]).slice(0,15)')
            assert page.locator('#viewerBlock').evaluate('el => el.scrollWidth <= el.clientWidth'), overflow
            assert not errors
        finally:
            browser.close()


def test_precision_workspace_preserves_stages_and_grows_notes(server_url, tmp_path):  # noqa: F811
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 1100})
        try:
            page.goto(server_url, wait_until='networkidle')
            page.locator('#sampleLaunch').click()
            page.locator('[data-gstep-nav="details"]').click()
            expect(page.locator('#sampleReloadPainting')).to_be_enabled(timeout=90000)
            page.locator('[data-gstep-nav="plan"]').click()
            before = page.locator('#planJson').input_value()
            visit = page.locator('#samplePaintedVisit').input_value()
            page.get_by_role('link', name='Edit Tooth Precision').click()
            dialog = page.get_by_role('dialog', name='Edit Tooth Precision')
            expect(dialog).to_be_visible()
            editor = page.frame_locator('.precision-dialog iframe')
            expect(editor.locator('#reviewSource')).to_contain_text('week 7' if visit == 'progress-01' else 'week 1', timeout=60000)
            notes = editor.locator('#reviewNotes')
            page.screenshot(path=str(tmp_path/'painting-overlay.png'))
            original_height = notes.bounding_box()['height']
            notes.fill('\n'.join(f'Observation {n}' for n in range(25)))
            assert notes.bounding_box()['height'] > original_height + 100
            assert notes.bounding_box()['width'] > 700
            page.once('dialog', lambda prompt: prompt.dismiss())
            page.locator('#precisionBack').click()
            expect(dialog).to_be_visible()
            page.once('dialog', lambda prompt: prompt.accept())
            page.locator('#precisionBack').click()
            expect(dialog).not_to_be_visible()
            expect(page.locator('[data-gstep="plan"]')).to_have_class('gstep is-active')
            assert page.locator('#planJson').input_value() == before
        finally:
            browser.close()


def test_uploaded_scan_dates_survive_reload_without_inferred_capture_date(server_url, tmp_path):  # noqa: F811
    from test_boundary_intake import surface
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1280, 'height': 1000})
        try:
            page.goto(server_url, wait_until='networkidle')
            page.locator('#teethProfile').click()
            page.locator('#simpleStlFile').set_input_files(surface(tmp_path))
            date = page.locator('#scanDates input[type="date"]')
            expect(date).to_have_value('')
            expect(page.locator('#scanDates')).to_contain_text('Uploaded')
            date.fill('2026-10-21')
            expect(page.locator('#scanDates [role="status"]')).to_contain_text('saved')
            page.reload(wait_until='networkidle')
            page.locator('#teethProfile').click()
            expect(date).to_have_value('2026-10-21')
            page.locator('#sampleLaunch').click()
            page.locator('#teethProfile').click()
            expect(date).to_have_value('2026-10-21')
        finally:
            browser.close()

"""Audit regressions exercise real browser state, IndexedDB and modal boundaries."""
import base64
import hashlib
import json

import pytest
pytest.importorskip('playwright.sync_api')
from playwright.sync_api import expect, sync_playwright  # noqa: E402
from test_chat_workspace import server_url  # noqa: E402,F401
from test_boundary_intake import surface  # noqa: E402


def test_sample_mode_switch_preserves_edits_and_failed_reload_is_atomic(server_url):  # noqa: F811
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={'width': 1440, 'height': 1100})
        requests = []
        page.on('request', lambda req: requests.append(req.url) if req.url.endswith('/api/sample-teeth') else None)
        try:
            page.goto(server_url)
            page.locator('#sampleLaunch').click()
            page.locator('[data-gstep-nav="details"]').click()
            expect(page.locator('#sampleReloadPainting')).to_be_enabled(timeout=90000)
            # Seed a proposed movement without requiring unverified scan units to
            # be confirmed. This is state preservation, not a clinical motion test.
            before = page.evaluate('''async () => {
              const { state } = await import('/state.js');
              state.rows[0].x = 0.2;
              state.manualEdit.undoStack.push(structuredClone(state.rows));
              return JSON.stringify({rows:state.rows, sources:state.scanSources, applied:state.segmentation.applied, visit:state.sample.visit});
            }''')
            page.locator('[data-sample-view="observed"]').click()
            page.locator('[data-sample-view="simulation"]').click()
            expect(page.locator('#sampleReloadPainting')).to_be_enabled()
            assert len(requests) == 1
            page.route('**/api/sample-teeth', lambda route: route.fulfill(status=503, json={'ok': False, 'errors': ['Reload unavailable']}))
            page.once('dialog', lambda dialog: dialog.accept())
            previous_visit = json.loads(before)['visit']
            page.locator('#samplePaintedVisit').select_option('initial' if previous_visit == 'progress-01' else 'progress-01')
            expect(page.locator('#sampleReloadPainting')).to_be_enabled()
            page.wait_for_function("async () => (await import('/state.js')).state.segmentation.status === 'Reload unavailable'")
            after = page.evaluate('''async () => {
              const { state } = await import('/state.js');
              return JSON.stringify({rows:state.rows, sources:state.scanSources, applied:state.segmentation.applied, visit:state.sample.visit});
            }''')
            assert after == before
            expect(page.locator('#samplePaintedVisit')).to_have_value(previous_visit)
        finally:
            browser.close()


def test_personal_painting_and_notes_resume_and_conflicts_do_not_overwrite(server_url, tmp_path):  # noqa: F811
    source = surface(tmp_path)
    labels = bytes([31, 32]) + bytes(286)
    correction_file = tmp_path/'labels.json'
    correction_file.write_text(json.dumps({'schema': 'ortho-region-corrections-v1',
        'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(), 'arch': 'lower',
        'face_count': len(labels), 'labels_base64': base64.b64encode(labels).decode(),
        'reviewed': False, 'provenance': 'user-corrected'}))
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        context = browser.new_context(viewport={'width': 1440, 'height': 1100})
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        try:
            page.goto(server_url)
            page.locator('#teethProfile').click()
            page.locator('#simpleStlFile').set_input_files(source)
            page.locator('#openBoundaryEditor').click()
            editor = page.frame_locator('.precision-dialog iframe')
            expect(editor.locator('#reviewSaveLocal')).to_be_enabled()
            editor.locator('#reviewLabels').set_input_files(correction_file)
            expect(editor.locator('#reviewSaveStatus')).to_contain_text('Unsaved')
            editor.locator('#reviewNotes').fill('Saved personal note')
            editor.locator('#reviewSaveLocal').click()
            expect(editor.locator('#reviewSaveStatus')).to_contain_text('Saved lower draft locally')
            page.locator('#precisionBack').click()
            page.locator('[data-step-target="notes"]').click()
            card = page.locator('.painting-note').filter(has_text='Saved personal note')
            expect(card).to_be_visible()
            card.get_by_role('link', name='Open painting & notes').click()
            expect(page.locator('#precisionBack')).to_have_text('← Back to saved notes')
            expect(editor.locator('#reviewNotes')).to_have_value('Saved personal note')
            expect(editor.locator('#reviewChecked')).not_to_be_checked()
            with page.expect_download() as download:
                editor.locator('#reviewExport').click()
            destination = tmp_path/'resumed.json'
            download.value.save_as(destination)
            assert json.loads(destination.read_text())['labels_base64'] == base64.b64encode(labels).decode()
            second = context.new_page()
            second.goto(page.locator('.precision-dialog iframe').get_attribute('src'))
            expect(second.locator('#reviewNotes')).to_have_value('Saved personal note')
            editor.locator('#reviewNotes').fill('Newer saved note')
            editor.locator('#reviewSaveLocal').click()
            expect(editor.locator('#reviewSaveStatus')).to_contain_text('Saved lower draft locally')
            second.locator('#reviewNotes').fill('Stale editor note')
            second.locator('#reviewSaveLocal').click()
            expect(second.locator('#reviewSaveStatus')).to_contain_text('newer painting was saved')
            second.close()
            page.locator('#precisionBack').click()
            card = page.locator('.painting-note').filter(has_text='Newer saved note')
            expect(card).to_be_visible()
            page.reload(wait_until='networkidle')
            page.locator('[data-step-target="notes"]').click()
            expect(card).to_be_visible()
            card.get_by_role('link', name='Open painting & notes').click()
            expect(editor.locator('#reviewNotes')).to_have_value('Newer saved note')
            assert not errors
        finally:
            browser.close()

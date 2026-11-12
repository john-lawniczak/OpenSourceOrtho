"""Regression coverage for stale asynchronous results and sample boundaries."""
import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect, sync_playwright  # noqa: E402
from test_chat_workspace import server_url  # noqa: E402,F401


@pytest.mark.parametrize("change", ["title", "segmentation", "landmarks"])
def test_generation_discards_results_after_workspace_changes(server_url, change):  # noqa: F811 - pytest fixture injection
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        pending = []
        try:
            page.goto(server_url, wait_until="networkidle")
            page.route('**/api/generate-plan', lambda route: pending.append(route))
            page.evaluate("""async () => {
              const {state} = await import('/state.js'); state.userMode = 'advanced';
              window.generationDone = import('/generation.js').then(m => m.generatePlan());
            }""")
            page.wait_for_timeout(200)
            assert len(pending) == 1
            before = page.evaluate("async () => JSON.stringify((await import('/state.js')).state.rows)")
            page.evaluate("""async change => {
              const {state} = await import('/state.js');
              if (change === 'title') document.getElementById('planTitle').value = 'Different case';
              else if (change === 'segmentation') state.segmentation = {...state.segmentation};
              else state.generation.landmarks = {new: 'landmarks'};
            }""", change)
            pending[0].fulfill(json={"ok": True, "source": "fake", "correctness": {"verdict": "pass"},
                "plan": {"stages": [{"index": 0, "deltas": [{"tooth": {"value": "21"}, "translate_x_mm": 2}]}]}})
            page.evaluate("() => window.generationDone")
            assert page.evaluate("async () => JSON.stringify((await import('/state.js')).state.rows)") == before
            assert 'working plan changed' in page.evaluate("async () => (await import('/state.js')).state.generation.status")
        finally:
            browser.close()


def test_sample_from_reference_does_not_leak_controls(server_url):  # noqa: F811 - pytest fixture injection
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(server_url, wait_until="networkidle")
            page.evaluate("""() => {
              document.getElementById('fixedTeeth').value = '21';
              document.getElementById('capLinear').value = '.17';
            }""")
            page.locator('[data-step-target="glossary"]').click()
            page.locator('#sampleLaunch').click()
            expect(page.locator('.gstep[data-gstep="plan"]')).to_be_visible()
            expect(page.locator('#fixedTeeth')).to_have_value('')
            page.evaluate("() => { document.getElementById('fixedTeeth').value = '11'; }")
            page.locator('#teethProfile').click()
            expect(page.locator('#fixedTeeth')).to_have_value('21')
            expect(page.locator('#capLinear')).to_have_value('.17')
            expect(page.locator('#simpleStlFile')).to_be_enabled()
        finally:
            browser.close()


def test_scan_loading_rejects_stale_geometry_and_retries_failures(server_url):  # noqa: F811 - pytest fixture injection
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(server_url, wait_until="networkidle")
            result = page.evaluate("""async () => {
              const {createViewer} = await import('/viewer3d.js');
              const host = document.createElement('div'); host.style = 'width:500px;height:400px';
              document.body.append(host); const viewer = createViewer(host);
              const bytes = width => new TextEncoder().encode(`solid scan\nfacet normal 0 0 1\nouter loop\nvertex 0 0 0\nvertex ${width} 0 0\nvertex 0 2 1\nendloop\nendfacet\nendsolid`).buffer;
              let resolveOld;
              const old = viewer.loadScanSources([{name:'old.stl', file:{size:1, lastModified:1,
                arrayBuffer: () => new Promise(resolve => { resolveOld = resolve; })}}]);
              await viewer.loadScanSources([{name:'new.stl', file:{size:1, lastModified:2,
                arrayBuffer: async () => bytes(2)}}]);
              resolveOld(bytes(100)); const oldResult = await old;
              const width = viewer.scanExtentMm().x;
              let fail = true;
              const source = {name:'retry.stl', file:{size:1, lastModified:3,
                arrayBuffer: async () => { if (fail) throw new Error('temporary'); return bytes(3); }}};
              try { await viewer.loadScanSources([source]); } catch {}
              fail = false;
              const retry = await viewer.loadScanSources([source]);
              viewer.dispose(); host.remove();
              return {stale: oldResult.stale, width, retry:retry.count};
            }""")
            assert result == {"stale": True, "width": 2, "retry": 1}
        finally:
            browser.close()

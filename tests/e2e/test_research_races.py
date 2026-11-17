"""Delayed reads must not silently replace a newer research selection."""

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect, sync_playwright  # noqa: E402
from test_chat_workspace import server_url  # noqa: E402,F401
from orthoplan.io.stl_export import binary_stl_bytes  # noqa: E402


def delay_scan_reads(page):
    page.evaluate("""() => {
      const original = File.prototype.arrayBuffer;
      window.scanReads = [];
      File.prototype.arrayBuffer = function() {
        return new Promise(resolve => window.scanReads.push(() => resolve(original.call(this))));
      };
    }""")


def test_concurrent_endpoint_imports_and_stale_arch_read(server_url, tmp_path):  # noqa: F811
    scan = tmp_path / "capture.stl"
    scan.write_bytes(binary_stl_bytes([[(0, 0, 0), (1, 0, 0), (0, 1, 0)]]))
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        try:
            page.goto(server_url + "/progress.html")
            delay_scan_reads(page)
            page.locator("#scan0").set_input_files(scan)
            expect(page.locator("#scan0")).to_be_disabled()
            page.locator("#scan1").set_input_files(scan)
            assert page.evaluate("scanReads.length") == 2
            page.evaluate("scanReads.splice(0).forEach(f => f())")
            for index in (0, 1):
                expect(page.locator(f"#activeCapture{index} option")).to_have_count(2)
            page.locator("#caseName").fill("Original case")
            page.locator("#saveCase").click()
            expect(page.locator("#caseStatus")).to_contain_text("Case saved locally")
            page.locator("#scan0").set_input_files(scan)
            page.locator("#caseArch").select_option("lower")
            page.evaluate("scanReads.splice(0).forEach(f => f())")
            expect(page.locator("#caseStatus")).to_contain_text("changed during import")
            expect(page.locator("#activeCapture0 option")).to_have_count(1)
            page.locator("#openCase").click()
            expect(page.locator("#caseStatus")).to_contain_text("Opened Original case")
            expect(page.locator("#activeCapture0 option")).to_have_count(2)
        finally:
            browser.close()


def research_host(page, url):
    page.goto(url + "/progress.html", wait_until="networkidle")
    page.evaluate("""async () => {
      window.requests = []; window.reloads = 0;
      window.fetch = url => new Promise(resolve => requests.push({url, resolve}));
      window.answer = (index, body) => requests[index].resolve({ok:true, json:async () => body});
      const host = document.createElement('div'); document.body.prepend(host);
      const {installSampleResearch} = await import('/sample_research.js');
      installSampleResearch(host, async () => { reloads++; });
      host.querySelector('details').open = true;
    }""")


def fit_list(arch):
    return {"ok": True, "inputs": {"annotations": [{"visit": arch, "origin": "test"}]},
            "input_digest": arch, "versions": [{"id": arch + "-fit",
            "created_at": "2026-11-16", "stale": False,
            "summary": {"fitted": 1, "regions": 1, "uncertain": 0, "unmatched": 0}}]}


def test_imported_labels_stay_with_capture_before_any_fit(server_url, tmp_path):  # noqa: F811
    scans = []
    for index in (1, 2):
        scan = tmp_path / f"capture-{index}.stl"
        scan.write_bytes(binary_stl_bytes([[(0, 0, 0), (1, 0, 0), (0, index, 0)]]))
        scans.append(scan)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        try:
            page.goto(server_url + "/progress.html")
            page.locator("#scan0").set_input_files(scans)
            expect(page.locator("#activeCapture0 option")).to_have_count(3)
            page.locator("#activeCapture0").select_option(label="capture-1.stl")
            page.locator("#scan1").set_input_files(scans[1])
            expect(page.locator("#activeCapture1 option")).to_have_count(2)
            correction = page.evaluate("""async () => {
              const {RegionEdits} = await import('/region_edits.js');
              const sha = document.querySelector('#activeCapture0').value.split(':')[1];
              return JSON.stringify(new RegionEdits(new Uint8Array([11]), 'upper').export(sha));
            }""")
            page.locator("#correction0").set_input_files({
                "name": "labels.json", "mimeType": "application/json", "buffer": correction.encode(),
            })
            expect(page.locator("#caseStatus")).to_contain_text("Labels retained")
            page.locator("#activeCapture0").select_option(label="capture-2.stl")
            page.locator("#activeCapture0").select_option(label="capture-1.stl")
            page.locator("#caseName").fill("Painted captures")
            page.locator("#saveCase").click()
            expect(page.locator("#caseStatus")).to_contain_text("Case saved locally")
            saved = page.evaluate("""async () => {
              const {caseStore} = await import('/progress_case_store.js');
              return (await caseStore('get', 'Painted captures')).corrections[0];
            }""")
            assert saved["labels_base64"] == "Cw=="
        finally:
            browser.close()


def test_research_ignores_out_of_order_arch_and_fit_responses(server_url):  # noqa: F811
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        try:
            research_host(page, server_url)
            page.locator('[data-research="refresh"]').click()
            page.locator('[data-research="arch"]').select_option("lower")
            page.evaluate("body => answer(1, body)", fit_list("lower"))
            expect(page.locator('[data-research="status"]')).to_contain_text("lower")
            page.evaluate("body => answer(0, body)", fit_list("upper"))
            expect(page.locator('[data-research="fit"] option').last).to_have_attribute("value", "lower-fit")
            page.locator('[data-research="fit"]').select_option("lower-fit")
            page.locator('[data-research="fit"]').select_option("")
            page.evaluate("() => answer(2, {ok:true, stale:false, record:{summary:{fitted:1}}})")
            expect(page.locator('[data-research="status"]')).to_contain_text("Showing the bundled fit")
            assert page.evaluate("reloads") == 1
        finally:
            browser.close()


def test_research_build_locks_before_refresh_and_cancel_starts_no_job(server_url):  # noqa: F811
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        try:
            research_host(page, server_url)
            page.locator('[data-research="build"]').click()
            expect(page.locator('[data-research="build"]')).to_be_disabled()
            expect(page.locator('[data-research="arch"]')).to_be_disabled()
            page.locator('[data-research="cancel"]').click()
            page.evaluate("body => answer(0, body)", fit_list("upper"))
            expect(page.locator('[data-research="build"]')).to_be_enabled()
            assert page.evaluate("requests.length") == 1
            assert page.evaluate("reloads") == 0
        finally:
            browser.close()

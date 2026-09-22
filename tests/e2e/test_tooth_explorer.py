"""Tooth selection, actual WebGL colors, and navigation isolation."""
from __future__ import annotations

import base64
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect, sync_playwright  # noqa: E402

from orthoplan.server import Handler  # noqa: E402


@pytest.fixture(scope="module")
def server_url():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_address[1]}"
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)


def rendered_colors(page):
    png = page.locator("#toothExplorerViewer canvas").screenshot()
    return page.evaluate("""async data => {
      const image = new Image(); image.src = data; await image.decode();
      const canvas = document.createElement('canvas');
      canvas.width = image.width; canvas.height = image.height;
      const ctx = canvas.getContext('2d'); ctx.drawImage(image, 0, 0);
      const pixels = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
      const count = {blue: 0, red: 0, bluePoint: null};
      let blueRun = 0;
      for (let i = 0; i < pixels.length; i += 4) {
        const [r, g, b] = pixels.slice(i, i + 3);
        if (b > r + 35 && b > g + 20) {
          count.blue++; blueRun++;
          if (blueRun === 5 && !count.bluePoint) {
            count.bluePoint = {x: (i / 4) % canvas.width - 2, y: Math.floor(i / 4 / canvas.width)};
          }
        } else { blueRun = 0; }
        if (r > g + 35 && r > b + 35) count.red++;
      }
      return count;
    }""", "data:image/png;base64," + base64.b64encode(png).decode())


def test_tooth_explorer_selection_and_rendering(server_url: str, tmp_path: Path):
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1100})
        errors = []
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        try:
            page.goto(server_url, wait_until="networkidle")
            original_plan = page.locator("#planJson").input_value()
            page.get_by_role("button", name="Open the tooth map and numbering").click()
            canvas = page.locator("#toothExplorerViewer canvas")
            expect(canvas).to_be_visible()
            baseline = rendered_colors(page)
            page.locator("#toothExplorerInput").fill("11, 12; 33 34 43 44 11")
            page.get_by_role("button", name="Highlight teeth", exact=True).click()
            expect(page.locator("#toothExplorerSummary")).to_have_text(
                "6 teeth selected: 11, 12, 33, 34, 43, 44."
            )
            expect(page.locator('#toothExplorerGrid button[aria-pressed="true"]')).to_have_count(6)
            expect(page.locator("#toothExplorerList")).to_contain_text("33 · Lower left canine")
            blue = rendered_colors(page)
            assert blue["blue"] > baseline["blue"] + 100
            page.locator("#toothExplorerViewer").screenshot(path=str(tmp_path / "blue-teeth.png"))
            canvas.click(position=blue["bluePoint"])
            expect(page.locator('#toothExplorerGrid button[aria-pressed="true"]')).to_have_count(5)
            page.get_by_role("button", name="Try 11, 12, 33, 34, 43, 44", exact=True).click()
            page.get_by_role("button", name="Red", exact=True).click()
            red = rendered_colors(page)
            assert red["red"] > blue["red"] + 100
            assert red["blue"] < blue["blue"]
            page.locator("#toothExplorerInput").fill("11 19 <bad>")
            page.get_by_role("button", name="Highlight teeth", exact=True).click()
            expect(page.locator("#toothExplorerError")).to_contain_text("Selection unchanged")
            expect(page.locator('#toothExplorerGrid button[aria-pressed="true"]')).to_have_count(6)
            page.get_by_role("button", name="FDI 11: Upper right central incisor", exact=True).press("Space")
            expect(page.locator("#toothExplorerSummary")).to_contain_text("5 teeth selected")
            expect(page.locator("#toothExplorerError")).to_be_empty()
            page.get_by_role("button", name="Yellow", exact=True).click()
            page.locator("#toothExplorerColor").fill("#8b5cf6")
            expect(page.locator("#toothExplorerColor")).to_have_value("#8b5cf6")
            page.locator('#panel-toothmap [data-info-back]').click()
            page.get_by_role("button", name="Open the tooth map and numbering").click()
            expect(canvas).to_be_visible()
            expect(page.locator("#toothExplorerSummary")).to_contain_text("5 teeth selected")
            page.get_by_role("button", name="Clear", exact=True).click()
            expect(page.locator('#toothExplorerGrid button[aria-pressed="true"]')).to_have_count(0)
            page.get_by_role("button", name="Try 11, 12, 33, 34, 43, 44", exact=True).click()
            expect(page.locator('#toothExplorerGrid button[aria-pressed="true"]')).to_have_count(6)
            page.locator("#themeToggle").click()
            page.set_viewport_size({"width": 390, "height": 844})
            canvas.scroll_into_view_if_needed()
            expect(canvas).to_be_visible()
            assert page.locator("#toothExplorer").evaluate(
                "element => element.scrollWidth <= element.clientWidth"
            )
            page.locator("#toothExplorer").screenshot(path=str(tmp_path / "mobile-dark-explorer.png"))
            assert page.locator("#planJson").input_value() == original_plan
        finally:
            browser.close()
        assert not errors


def test_tooth_explorer_controls_survive_unavailable_3d(server_url: str):
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.add_init_script("""(() => {
              const getContext = HTMLCanvasElement.prototype.getContext;
              HTMLCanvasElement.prototype.getContext = function(kind, ...args) {
                return kind.startsWith('webgl') ? null : getContext.call(this, kind, ...args);
              };
            })();""")
            page.goto(server_url, wait_until="networkidle")
            page.get_by_role("button", name="Open the tooth map and numbering").click()
            expect(page.locator("#toothExplorerViewer")).to_contain_text("3D is unavailable")
            page.get_by_role("button", name="FDI 44: Lower right first premolar", exact=True).click()
            expect(page.locator("#toothExplorerSummary")).to_have_text("1 tooth selected: 44.")
            expect(page.locator("#toothExplorerList")).to_contain_text("Lower right first premolar")
        finally:
            browser.close()

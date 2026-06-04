"""Regenerate the UI screenshots in docs/images/.

Requires the e2e extra and a browser:

    pip install -e ".[e2e]" && python -m playwright install chromium
    python tools/capture_screenshots.py

Serves the real dev server and captures key screens headlessly. The UI uses only
synthetic default state, so the images contain no patient data.
"""

from __future__ import annotations

import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

from orthoplan.server import Handler

IMAGES = Path(__file__).resolve().parents[1] / "docs" / "images"


def main() -> None:
    IMAGES.mkdir(parents=True, exist_ok=True)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{port}"

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 960})
            page.goto(url, wait_until="networkidle")

            page.click('button.step[data-step="stages"]')
            # Add a couple of stages so the demo shows more than one tooth.
            page.click("#addStage")
            page.click("#addStage")
            page.wait_for_timeout(300)
            page.screenshot(path=str(IMAGES / "stage-builder.png"))

            page.click('button.step[data-step="review"]')
            page.wait_for_selector("#viewer3d canvas", state="attached", timeout=15000)
            # Overlay shows both current (ghost) and planned (solid) proxies.
            page.click('button.mode[data-view="overlay"]')
            page.fill("#exaggeration", "60")
            page.wait_for_timeout(800)  # let the scene settle
            page.screenshot(path=str(IMAGES / "review-3d.png"))

            browser.close()
        print(f"Wrote screenshots to {IMAGES}")
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Record the private painted sample walkthrough for Upload and Details.

Run with the development virtualenv (Playwright Chromium and ffmpeg required).
The recording includes private contributor-painted regions and stays in private/media.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
import threading
import time
from http.server import ThreadingHTTPServer
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orthoplan.server import Handler  # noqa: E402
from orthoplan.datasets import SAMPLE_CASE_DIR  # noqa: E402

OUTPUT = SAMPLE_CASE_DIR / "private/media"
from playwright.sync_api import expect, sync_playwright  # noqa: E402


def stamp(seconds):
    milliseconds = int(seconds * 1000)
    return f"{milliseconds // 3600000:02}:{milliseconds // 60000 % 60:02}:{milliseconds // 1000 % 60:02}.{milliseconds % 1000:03}"


def record(page):
    page.goto(page.base_url, wait_until="networkidle")
    page.locator("#sampleLaunch").click()
    page.locator('[data-sample-view="simulation"]').click()
    expect(page.locator('#sampleReloadPainting')).to_be_enabled(timeout=90000)
    page.locator('[data-gstep-nav="details"]').click()
    expect(page.locator('#guidedTeeth [data-select-tooth]')).to_have_count(28)
    page.locator('#guidedTeeth [data-select-tooth="11"]').click()
    page.wait_for_load_state("networkidle")
    page.locator('.scan-view-controls:visible [data-scan-view="face"]').click()
    page.locator("#viewer3d").evaluate("el => window.scrollTo(0, el.getBoundingClientRect().top + window.scrollY - 220)")
    page.wait_for_timeout(1500)
    start, cues = time.monotonic(), []

    def show_viewer():
        page.locator("#viewer3d").evaluate("el => window.scrollTo(0, el.getBoundingClientRect().top + window.scrollY - 220)")

    def caption(text):
        cues.append((time.monotonic() - start, text))

    caption("USER_ONE week 7: 28 contributor-painted regions. Amber identifies the selected tooth; boundaries are drafts.")
    page.screenshot(path=str(OUTPUT / "workflow-poster.jpg"), type="jpeg", quality=85)
    page.wait_for_timeout(3500)
    caption("Choose an FDI number to select its saved painted region on either arch.")
    for tooth in [21, 31, 41]:
        page.locator(f'#guidedTeeth [data-select-tooth="{tooth}"]').click()
        show_viewer()
        page.wait_for_timeout(1800)
    caption("Use the number selector for FDI or US numbering. US 8 selects FDI 11.")
    page.locator('#toothNumberSystem').select_option('US')
    page.locator('#toothNumberInput').fill('8')
    page.locator('#toothNumberForm button').click()
    page.wait_for_timeout(2500)
    page.locator("#viewer3d").evaluate("el => window.scrollTo(0, el.getBoundingClientRect().top + window.scrollY - 220)")
    caption("Focus selected tooth brings that painted region closer. Fit scan returns to the full arches.")
    page.locator('[data-viewer-focus]').click()
    page.wait_for_timeout(2500)
    page.locator('.scan-view-controls:visible [data-scan-view="fit"]').click()
    page.wait_for_timeout(1500)
    caption("Rotate turns the camera around the scan. Pan moves the view without changing teeth.")
    box = page.locator('#viewer3d canvas').bounding_box()
    x, y = box['x'] + box['width'] * .5, box['y'] + box['height'] * .5
    for mode, dx, dy in [('rotate', 100, 20), ('pan', -70, -30)]:
        page.locator(f'[data-viewer-drag="{mode}"]').click()
        page.mouse.move(x, y)
        page.mouse.down()
        page.mouse.move(x + dx, y + dy, steps=8)
        page.mouse.up()
        page.wait_for_timeout(1800)
    caption("Face-on restores the front view. The arch spacing is for viewing, not a measured bite.")
    page.locator('.scan-view-controls:visible [data-scan-view="face"]').click()
    page.locator('[data-viewer-drag="rotate"]').click()
    page.wait_for_timeout(2500)
    caption("Overlay compares exploratory poses with the source. No preset movement is added; week 7 scale remains unverified.")
    page.locator('[data-view="overlay"]').click()
    show_viewer()
    page.wait_for_timeout(3500)
    return start, time.monotonic(), cues


def encode_video(ffmpeg, video, offset, duration, cues):
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-ss", str(offset),
                    "-i", str(video.path()), "-t", str(duration), "-an",
                    "-c:v", "libvpx-vp9", "-crf", "34", "-b:v", "0", "-cpu-used", "4",
                    str(OUTPUT / "workflow-demo.webm")], check=True)
    return duration, cues


def main():
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise SystemExit("ffmpeg is required")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with tempfile.TemporaryDirectory(prefix="ortho-workflow-") as temp, sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 1080},
                                          record_video_dir=temp, record_video_size={"width": 1440, "height": 1080})
            origin = time.monotonic()
            page = context.new_page()
            page.base_url = f"http://127.0.0.1:{server.server_address[1]}"
            try:
                start, end, cues = record(page)
                video = page.video
            finally:
                context.close()
                browser.close()
            duration = end - start
            duration, cues = encode_video(ffmpeg, video, start - origin, duration, cues)
            lines = ["WEBVTT\n"]
            for index, (offset, text) in enumerate(cues):
                stop = cues[index + 1][0] if index + 1 < len(cues) else duration
                lines.append(f"{stamp(offset)} --> {stamp(stop)}\n{text}\n")
            (OUTPUT / "workflow-demo.vtt").write_text("\n".join(lines))
            print(f"Recorded {duration:.1f}s to {OUTPUT / 'workflow-demo.webm'}")
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()

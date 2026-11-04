#!/usr/bin/env python3
"""Record the bundled sample's real UI for the captioned Upload walkthrough.

Run with the development virtualenv (Playwright Chromium and ffmpeg required).
No external model, credentials, or user-uploaded files are used.
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
from playwright.sync_api import expect, sync_playwright  # noqa: E402


def stamp(seconds):
    milliseconds = int(seconds * 1000)
    return f"{milliseconds // 3600000:02}:{milliseconds // 60000 % 60:02}:{milliseconds // 1000 % 60:02}.{milliseconds % 1000:03}"


def record(page):
    page.goto(page.base_url, wait_until="networkidle")
    page.locator("#sampleLaunch").click()
    expect(page.locator('#guidedTeeth [data-select-tooth="11"]')).to_be_visible(timeout=90000)
    page.locator('#guidedTeeth [data-select-tooth="11"]').click()
    page.locator("#viewerBlock").evaluate("el => window.scrollTo(0, el.getBoundingClientRect().top + window.scrollY - 72)")
    page.wait_for_timeout(1500)
    start = time.monotonic()
    cues = []

    def caption(text):
        cues.append((time.monotonic() - start, text))

    caption("Bundled sample: reviewed tooth segments, with a projected stage timeline.")
    page.screenshot(path=str(ROOT / "ui/workflow-poster.jpg"), type="jpeg", quality=80)
    page.wait_for_timeout(2500)
    caption("Select a crown or its FDI number below the viewer. Amber marks the selected tooth.")
    page.locator('#guidedTeeth [data-select-tooth="12"]').click()
    page.wait_for_timeout(1200)
    page.locator('#guidedTeeth [data-select-tooth="11"]').click()
    page.wait_for_timeout(1200)
    caption("Ask for an explicit geometric change. The local helper needs no API key.")
    page.locator("#askSelectedTooth").click()
    page.locator("#chatInput").fill("move 0.6 mm right")
    page.wait_for_timeout(1800)
    page.locator("#sendChat").click()
    expect(page.locator("#applyGoalPreview")).to_be_enabled(timeout=60000)
    page.wait_for_timeout(1800)
    page.locator("#toggleChatPanel").click()
    caption("Inspect the proposal, then Apply or Discard. It has not changed the saved working plan yet.")
    page.locator("#goalPreviewPanel").scroll_into_view_if_needed()
    page.wait_for_timeout(2200)
    page.locator("#applyGoalPreview").click()
    caption("Drag through each stage and its projected weeks. Current returns to the original scan.")
    page.locator("#viewerBlock").evaluate("el => window.scrollTo(0, el.getBoundingClientRect().top + window.scrollY - 72)")
    slider = page.locator("#stageSlider")
    last = int(slider.get_attribute("max"))
    for stage in range(last + 1):
        slider.fill(str(stage))
        page.wait_for_timeout(900)
    page.locator('[data-view="current"]').click()
    page.wait_for_timeout(1800)
    page.locator('[data-view="planned"]').click()
    page.wait_for_timeout(1800)
    caption("Use Undo to restore the prior plan. This is a geometric preview, not a predicted treatment outcome.")
    page.locator("#guidedEditUndo").click()
    page.wait_for_timeout(2000)
    return start, time.monotonic(), cues


def encode_video(ffmpeg, video, offset, duration, cues):
    # Keep the request/result interactions while shortening idle computation.
    cut_from, cut_to = cues[2][0] + 5, cues[3][0] - 2
    options = []
    if cut_to > cut_from + 2:
        filters = (f"[0:v]trim=end={cut_from},setpts=PTS-STARTPTS[a];"
                   f"[0:v]trim=start={cut_to}:end={duration},setpts=PTS-STARTPTS[b];"
                   "[a][b]concat=n=2:v=1:a=0[v]")
        options = ["-filter_complex", filters, "-map", "[v]"]
        removed = cut_to - cut_from
        duration -= removed
        cues = [(stamp - removed if stamp >= cut_to else stamp, text) for stamp, text in cues]
        cues[2] = (cues[2][0], cues[2][1] + " Processing time shortened in this video.")
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-ss", str(offset),
                    "-i", str(video.path()), *options, "-t", str(duration), "-an",
                    "-c:v", "libvpx-vp9", "-crf", "34", "-b:v", "0", "-cpu-used", "4",
                    str(ROOT / "ui/workflow-demo.webm")], check=True)
    return duration, cues


def main():
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise SystemExit("ffmpeg is required")
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
            (ROOT / "ui/workflow-demo.vtt").write_text("\n".join(lines))
            print(f"Recorded {duration:.1f}s to ui/workflow-demo.webm")
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()

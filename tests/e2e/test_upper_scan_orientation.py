"""Real STL conventions render upper crown tips below the base in every front preset."""
import base64
import io
import json
import struct

import pytest

pytest.importorskip("playwright.sync_api")
from PIL import Image
from playwright.sync_api import expect
from test_region_baseline_workflow import review_page, server_url  # noqa: F401
from test_boundary_intake import export
from orthoplan.datasets import SAMPLE_CASE_DIR
from orthoplan.region_corrections import baseline_source, save_baseline_corrections


def crown_colors_below_base(png):
    image = Image.open(io.BytesIO(png)).convert("RGB")
    crown, base = [], []
    for y in range(image.height):
        for x in range(image.width):
            r, g, b = image.getpixel((x, y))
            if r > g * 1.3 and b > g * 1.3 and max(r, b) > 70:
                crown.append(y)
            elif max(r, g, b) - min(r, g, b) < 35 and min(r, g, b) > 70:
                base.append(y)
    assert len(crown) > 100 and len(base) > 100
    assert sum(crown) / len(crown) > sum(base) / len(base) + 8


def view_only_labels(visit):
    source = baseline_source("upper", visit)
    raw = (SAMPLE_CASE_DIR / source["filename"]).read_bytes()
    heights = [sum((f[5], f[8], f[11])) / 3 for f in struct.iter_unpack("<12fH", raw[84:])]
    midpoint = (min(heights) + max(heights)) / 2
    # Diagnostic colors mark the crown-bearing half, not anatomical segmentation.
    labels = bytes(11 if (z < midpoint if visit == "initial" else z > midpoint) else 0 for z in heights)
    return source, {"schema": "ortho-region-corrections-v1", "source_sha256": source["sha256"],
                    "arch": "upper", "face_count": len(labels), "labels_base64": base64.b64encode(labels).decode(),
                    "reviewed": False, "provenance": "automatic-draft"}


@pytest.mark.parametrize("visit", ["initial", "progress-01"])
def test_upper_front_presets_and_reimports_keep_tips_down(review_page, server_url, tmp_path, visit):  # noqa: F811
    page = review_page
    source, correction = view_only_labels(visit)
    assert save_baseline_corrections({"arch": "upper", "visit": visit, "corrections": correction},
                                     root=tmp_path / "snapshots")["ok"]
    page.goto(server_url + f"/region-review.html?baseline=upper&visit={visit}")
    expect(page.locator("#reviewSource")).to_contain_text(source["filename"], timeout=30000)
    canvas = page.locator("#regionCanvas canvas")
    crown_colors_below_base(canvas.screenshot())
    for command in ["default", "face", "auto"]:
        page.locator('[data-scan-view="roll-left"]').click()
        page.locator(f'[data-scan-view="{command}"]').click()
        crown_colors_below_base(canvas.screenshot(path=str(tmp_path / f"{visit}-{command}.png")))
    assert export(page, tmp_path, "after-presets.json") == correction
    # Own STL and the sample route must agree even when the name is arbitrary.
    renamed = tmp_path / "another_upper_scan.stl"
    renamed.write_bytes((SAMPLE_CASE_DIR / source["filename"]).read_bytes())
    page.locator("#reviewScan").set_input_files(renamed)
    expect(page.locator("#reviewSource")).to_contain_text(renamed.name)
    record = tmp_path / "diagnostic-colors.json"
    record.write_text(json.dumps(correction))
    page.locator("#reviewLabels").set_input_files(record)
    expect(page.locator("#reviewSaveStatus")).to_contain_text("Unsaved changes")
    page.locator('[data-scan-view="default"]').click()
    crown_colors_below_base(canvas.screenshot(path=str(tmp_path / f"{visit}-reimport.png")))
    restored = export(page, tmp_path, "reimport-export.json")
    assert restored["source_sha256"] == correction["source_sha256"]
    assert restored["labels_base64"] == correction["labels_base64"]

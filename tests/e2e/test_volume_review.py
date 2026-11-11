import base64
import hashlib
import json
import struct
import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect, sync_playwright  # noqa:E402
from test_chat_workspace import server_url  # noqa:E402,F401
from orthoplan.datasets import SAMPLE_CASE_DIR  # noqa:E402


def test_volume_seed_grow_and_affine_mask_export(server_url, tmp_path):  # noqa:F811
    values = [
        1000 if all(2 <= v <= 4 for v in (x, y, z)) else 0
        for z in range(8)
        for y in range(8)
        for x in range(8)
    ]
    raw = struct.pack("<512f", *values)
    packet = dict(
        schema="ortho-volume-review-v1",
        frame="dicom-patient-lps-mm",
        dtype="float32-le",
        dimensions_xyz=[8, 8, 8],
        voxel_to_patient_mm=[[0, -1, 0, 10], [1, 0, 0, 20], [0, 0, 1, 30], [0, 0, 0, 1]],
        voxel_spacing_mm=[1, 1, 1],
        source_digest="a" * 64,
        pixel_sha256=hashlib.sha256(raw).hexdigest(),
        pixels_base64=base64.b64encode(raw).decode(),
        intensity_range=[0, 1000],
        source_slices=8,
        stride=1,
    )
    path = tmp_path / "volume.json"
    path.write_text(json.dumps(packet))
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        try:
            page.goto(server_url + "/volume-review.html")
            page.locator("#volumeFile").set_input_files(path)
            expect(page.locator("#volumeStatus")).to_contain_text("Loaded 8 source slices")
            canvas = page.locator("#volumeCanvas")
            box = canvas.bounding_box()
            canvas.click(position={"x": box["width"] * 0.45, "y": box["height"] * 0.45})
            expect(page.locator("#seedPosition")).to_contain_text("patient LPS")
            page.locator("#growVolume").click()
            expect(page.locator("#volumeStatus")).to_contain_text("27 labeled voxels")
            page.locator("#volumePlane").select_option("sagittal")
            expect(page.locator("#sliceLabel")).to_contain_text("sagittal")
            with page.expect_download() as event:
                page.locator("#exportVolumeMasks").click()
            exported = tmp_path / "masks.json"
            event.value.save_as(exported)
            mask = json.loads(exported.read_text())
            assert mask["reviewed"] is False
            assert len(mask["root_voxels_by_tooth"]["11"]) == 27
            assert mask["voxel_to_patient_mm"] == packet["voxel_to_patient_mm"]
            assert not errors
        finally:
            browser.close()


@pytest.mark.skipif(
    not (SAMPLE_CASE_DIR / ".local/cbct-review-volume.json").exists(),
    reason="Private local packet is not distributed",
)
def test_local_user_one_volume_displays_without_external_requests(server_url, tmp_path):  # noqa:F811
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1200, "height": 1000})
        external = []
        page.on(
            "request",
            lambda r: external.append(r.url) if not r.url.startswith(server_url) else None,
        )
        try:
            page.goto(server_url + "/volume-review.html")
            page.locator("#volumeFile").set_input_files(
                SAMPLE_CASE_DIR / ".local/cbct-review-volume.json"
            )
            expect(page.locator("#volumeStatus")).to_contain_text(
                "Loaded 824 source slices", timeout=30000
            )
            shades = page.locator("#volumeCanvas").evaluate(
                'c=>new Set(c.getContext("2d").getImageData(0,0,c.width,c.height).data).size'
            )
            assert shades > 20
            page.locator("#volumeCanvas").screenshot(path=str(tmp_path / "local-cbct-review.png"))
            assert not external
        finally:
            browser.close()

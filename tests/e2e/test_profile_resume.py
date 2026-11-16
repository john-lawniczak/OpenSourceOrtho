"""Legacy browser uploads remain in My profile; sample viewing never replaces them."""
import pytest
pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect, sync_playwright  # noqa: E402
from test_uploaded_intake import intake_server  # noqa: E402,F401
from test_local_profiles import value


def test_legacy_upload_and_autosave_survive_sample_navigation(intake_server):  # noqa: F811
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.on("dialog", lambda dialog: dialog.accept())
        try:
            page.goto(intake_server + "/region-review.html")
            page.evaluate("""async () => {
              const {saveUploadedFiles}=await import('/storage.js');
              const text='solid test\\nfacet normal 0 0 1\\nouter loop\\nvertex 0 0 0\\nvertex 60 0 0\\nvertex 0 40 0\\nendloop\\nendfacet\\nendsolid test\\n';
              await saveUploadedFiles([new File([text], 'legacy-upper.stl', {type:'model/stl'})]);
            }""")
            page.goto(intake_server)
            expect(page.locator("#profileSave")).to_be_enabled()
            assert page.evaluate("async () => (await import('/state.js')).state.files[0].name") == "legacy-upper.stl"
            value(page, "planTitle", "Automatically saved personal work")
            expect(page.locator("#profileSaveStatus")).to_contain_text("Saved locally", timeout=15000)
            page.reload()
            expect(page.locator("#planTitle")).to_have_value("Automatically saved personal work")
            page.locator("#sampleLaunch").click()
            page.wait_for_function("async () => (await import('/state.js')).state.sample.active")
            page.wait_for_timeout(1500)
            saved = page.evaluate("async () => (await (await import('/profile_store.js')).loadWorkspace()).data.fields.planTitle")
            assert saved == "Automatically saved personal work"
            page.reload()
            expect(page.locator("#planTitle")).to_have_value("Automatically saved personal work")
            assert page.evaluate("async () => (await import('/state.js')).state.files[0].name") == "legacy-upper.stl"
            assert not page.evaluate("async () => (await import('/state.js')).state.sample.active")
        finally:
            browser.close()

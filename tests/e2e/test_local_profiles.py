"""Local family workspaces survive reload without crossing profile boundaries."""

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect, sync_playwright  # noqa: E402
from test_uploaded_intake import intake_server  # noqa: E402,F401


def value(page, identity, text):
    page.locator(f"#{identity}").evaluate(
        "(el, text) => { el.value=text; el.dispatchEvent(new Event('input',{bubbles:true})); }",
        text,
    )


def save(page):
    page.locator("#profileSave").click()
    expect(page.locator("#profileSaveStatus")).to_contain_text("Saved locally", timeout=15000)


def add(page, name):
    page.locator("#profileAdd").click()
    page.locator("#profileName").fill(name)
    with page.expect_navigation(wait_until="domcontentloaded"):
        page.locator("#profileConfirm").click()
    expect(page.locator("#profileSelect option:checked")).to_have_text(name)
    expect(page.locator("#profileSave")).to_be_enabled()
    return page.locator("#profileSelect").input_value()


def switch(page, identity):
    with page.expect_navigation(wait_until="domcontentloaded"):
        page.locator("#profileSelect").select_option(identity)
    expect(page.locator("#profileSave")).to_be_enabled()
    page.wait_for_function(
        "id => document.querySelector('#profileSelect').value === id && !document.querySelector('main').inert",
        arg=identity,
    )


def prepare_parent(page, scan):
    page.locator("#simpleStlFile").set_input_files(scan)
    page.wait_for_function(
        "async () => (await import('/state.js')).state.scanSources.length === 1"
    )
    value(page, "planTitle", "Parent progress")
    value(page, "generationNotes", "Parent-only notes")
    value(page, "chatApiKey", "test-only-not-a-secret")
    await_state = """async () => {
      const {state}=await import('/state.js');
      state.rows=[{stage:1,tooth:'11',x:0.1,y:0,z:0,tip:0,torque:0,rotation:0,source:'manual'}];
      const {caseStore}=await import('/progress_case_store.js');
      await caseStore('put',{name:'boundary-family', scan:{filename:'parent.stl',arch:'upper'},notes:'Parent painting',saved_at:new Date().toISOString()},'edits');
      localStorage.setItem('orthoplan-plan-brief-v1:personal:draft-001','Parent discussion');
    }"""
    page.evaluate(await_state)
    save(page)


def check_other_tab_and_mobile(page, context, intake_server, other, tmp_path):  # noqa: F811
    # Another tab stays attached to its original profile after this tab switches.
    old = context.new_page()
    old.goto(intake_server)
    expect(old.locator("#profileSelect option:checked")).to_have_text("My profile")
    switch(page, other)
    expect(old.locator("#profileSelect option:checked")).to_have_text("My profile")
    assert (
        old.evaluate("async () => (await import('/profile_context.js')).activeProfileId")
        == "default"
    )
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    page.screenshot(path=str(tmp_path / "profiles-mobile.png"), full_page=True)


def test_three_profiles_restore_uploads_notes_edits_and_keep_old_tab_bound(
    intake_server, tmp_path, monkeypatch  # noqa: F811
):
    monkeypatch.setenv("ORTHOPLAN_REGION_CORRECTIONS", str(tmp_path / "labels"))
    monkeypatch.setenv("ORTHOPLAN_CASE_STORE", str(tmp_path / "cases.json"))
    scan = tmp_path / "family-upper.stl"
    scan.write_text(
        "solid test\nfacet normal 0 0 1\nouter loop\nvertex 0 0 0\nvertex 60 0 0\nvertex 0 40 0\nendloop\nendfacet\nendsolid test\n"
    )
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        context = browser.new_context(viewport={"width": 1440, "height": 1100})
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("dialog", lambda dialog: dialog.accept())
        try:
            page.goto(intake_server)
            expect(page.locator("#profileSelect option:checked")).to_have_text("My profile")
            expect(page.locator("#profileSave")).to_be_enabled()
            prepare_parent(page, scan)
            other = add(page, "Child A")
            expect(page.locator("#planTitle")).not_to_have_value("Parent progress")
            expect(page.locator("#chatApiKey")).to_have_value("")
            assert page.evaluate("async () => (await import('/state.js')).state.files.length") == 0
            assert (
                page.evaluate(
                    "async () => (await import('/progress_case_store.js')).listEditNotes()"
                )
                == []
            )
            value(page, "planTitle", "Child A progress")
            value(page, "generationNotes", "Child-only notes")
            save(page)
            third = add(page, "Child B")
            assert third != other
            value(page, "planTitle", "Child B progress")
            save(page)
            page.reload()
            expect(page.locator("#profileSelect option:checked")).to_have_text("Child B")
            expect(page.locator("#planTitle")).to_have_value("Child B progress")
            switch(page, other)
            expect(page.locator("#planTitle")).to_have_value("Child A progress")
            expect(page.locator("#generationNotes")).to_have_value("Child-only notes")
            switch(page, "default")
            expect(page.locator("#planTitle")).to_have_value("Parent progress")
            expect(page.locator("#generationNotes")).to_have_value("Parent-only notes")
            assert (
                page.evaluate("async () => (await import('/state.js')).state.files[0].text()")
                == scan.read_text()
            )
            assert page.evaluate("async () => (await import('/state.js')).state.rows[0].x") == 0.1
            page.locator('[data-step-target="notes"]').click()
            expect(page.locator(".painting-note")).to_contain_text("Parent painting")
            save(page)
            page.screenshot(path=str(tmp_path / "profiles-desktop.png"), full_page=True)
            check_other_tab_and_mobile(page, context, intake_server, other, tmp_path)
            assert not errors
        finally:
            browser.close()


def test_conflict_failed_save_and_duplicate_name_do_not_switch(intake_server):  # noqa: F811
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        context = browser.new_context()
        page, stale = context.new_page(), context.new_page()
        for tab in (page, stale):
            tab.on("dialog", lambda dialog: dialog.accept())
        try:
            page.goto(intake_server)
            expect(page.locator("#profileSave")).to_be_enabled()
            save(page)
            stale.goto(intake_server)
            expect(stale.locator("#profileSave")).to_be_enabled()
            value(page, "planTitle", "Newest progress")
            save(page)
            value(stale, "planTitle", "Stale progress")
            stale.locator("#profileSave").click()
            expect(stale.locator("#profileSaveStatus")).to_contain_text("another tab")
            assert (
                page.evaluate(
                    "async () => (await (await import('/profile_store.js')).loadWorkspace()).data.fields.planTitle"
                )
                == "Newest progress"
            )
            # Rename does not move any stored data, and duplicate names are rejected.
            page.locator("#profileRename").click()
            page.locator("#profileName").fill("Parent")
            page.locator("#profileConfirm").click()
            expect(page.locator("#profileSelect option:checked")).to_have_text("Parent")
            page.locator("#profileAdd").click()
            page.locator("#profileName").fill("Parent")
            page.locator("#profileConfirm").click()
            expect(page.locator("#profileError")).to_contain_text("already in use")
            page.locator("#profileCancel").click()
            # Simulate quota/storage failure; changing profile must not abandon current data.
            page.evaluate("""() => { const original=IDBDatabase.prototype.transaction;
              IDBDatabase.prototype.transaction=function(stores,mode,...rest) {
                if(this.name==='orthoplan-profiles' && mode==='readwrite') throw new DOMException('Storage full','QuotaExceededError');
                return original.call(this,stores,mode,...rest);
              }; }""")
            page.locator("#profileAdd").click()
            page.locator("#profileName").fill("Blocked child")
            page.locator("#profileConfirm").click()
            expect(page.locator("#profileError")).to_contain_text("Storage full")
            expect(page.locator("#profileSelect option:checked")).to_have_text("Parent")
        finally:
            browser.close()

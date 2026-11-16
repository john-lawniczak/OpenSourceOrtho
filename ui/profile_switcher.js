import { activeProfileId, selectProfile } from "./profile_context.js";
import { createProfile, listProfiles, loadWorkspace, renameProfile, saveWorkspace } from "./profile_store.js";
import { captureWorkspace, restoreWorkspace } from "./profile_snapshot.js";

export async function initializeProfiles({ state, render, restoreLegacy, leaveSample }) {
  const el = id => document.getElementById(id), main = document.querySelector("main");
  const status = message => { el("profileSaveStatus").textContent = message; };
  let revision = null, ready = false, dirty = false, timer, queue = Promise.resolve(), profiles = [], change = 0;
  main.inert = true;
  const updateList = async () => {
    profiles = await listProfiles();
    for (const id of ["profileSelect", "profileQuickSelect"]) {
      el(id).replaceChildren(...profiles.map(profile => new Option(profile.name, profile.id)));
      el(id).value = activeProfileId;
    }
    el("profileCurrentName").textContent = profiles.find(p => p.id === activeProfileId)?.name || "My profile";
  };
  function save() {
    clearTimeout(timer);
    if (!ready) return Promise.reject(new Error("Profile storage is not ready."));
    let data;
    try { data = captureWorkspace(state, document); }
    catch (error) { status(`Not saved: ${error.message}`); return Promise.reject(error); }
    const capturedChange = change;
    if (!data) { const error = new Error("Return to your profile and apply or discard the current preview before saving."); status(error.message); return Promise.reject(error); }
    dirty = true; status("Saving progress…");
    const request = queue.catch(() => {}).then(() => saveWorkspace(data, revision));
    queue = request.then(record => {
      revision = record.revision;
      if (queue === completion && capturedChange === change) { dirty = false; status(`Saved locally · ${new Date(record.savedAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`); }
    });
    const completion = queue;
    return completion.catch(error => { status(`Not saved: ${error.message}`); throw error; });
  }
  function schedule() {
    if (!ready || state.sample.active || state.goalPreview || state.goalBusy) return;
    dirty = true; change++; clearTimeout(timer); status("Unsaved progress…");
    timer = setTimeout(() => void save().catch(() => {}), 1200);
  }
  async function switchTo(id) {
    if (state.sample.active) { leaveSample(); render(); }
    await save();
    selectProfile(id);
    dirty = false;
    location.assign(location.pathname);
  }
  try {
    await updateList();
    if (!profiles.some(p => p.id === activeProfileId)) { selectProfile("default"); location.replace(location.pathname); return; }
    const saved = await loadWorkspace();
    if (saved) { restoreWorkspace(saved.data, state, document); revision = saved.revision; }
    else await restoreLegacy();
    render(); ready = true;
    status(saved ? "Saved progress restored" : "Progress saves automatically in this browser");
    for (const id of ["profileSelect", "profileQuickSelect", "profileAdd", "profileRename", "profileSave"]) el(id).disabled = false;
  } catch (error) { status(`Profile unavailable: ${error.message}`); }
  finally { main.inert = false; }
  el("profileSave").onclick = () => {
    if (state.sample.active) { leaveSample(); render(); }
    void save().catch(() => {});
  };
  for (const select of [el("profileSelect"), el("profileQuickSelect")]) select.onchange = async () => {
    const id = select.value;
    if (id === activeProfileId) return;
    for (const picker of [el("profileSelect"), el("profileQuickSelect")]) picker.disabled = true;
    try { await switchTo(id); }
    catch (error) {
      status(error.message);
      for (const picker of [el("profileSelect"), el("profileQuickSelect")]) { picker.value = activeProfileId; picker.disabled = false; }
      if (!el("chatSettingsDialog").open) el("chatSettingsDialog").showModal();
    }
  };
  const openName = mode => {
    el("profileForm").dataset.mode = mode;
    el("profileDialogTitle").textContent = mode === "add" ? "Add profile" : "Rename profile";
    el("profileName").value = mode === "add" ? "" : profiles.find(p => p.id === activeProfileId).name;
    el("profileError").textContent = "";
    el("profileDialog").showModal(); el("profileName").focus();
  };
  el("profileAdd").onclick = () => openName("add");
  el("profileRename").onclick = () => openName("rename");
  el("profileCancel").onclick = () => el("profileDialog").close();
  el("profileForm").onsubmit = async event => {
    event.preventDefault(); el("profileConfirm").disabled = true;
    try {
      if (el("profileForm").dataset.mode === "rename") {
        await renameProfile(activeProfileId, el("profileName").value); await updateList(); el("profileDialog").close();
      } else {
        if (state.sample.active) { leaveSample(); render(); }
        await save();
        const profile = await createProfile(el("profileName").value);
        selectProfile(profile.id); dirty = false; location.assign(location.pathname);
      }
    } catch (error) { el("profileError").textContent = error.message; }
    finally { el("profileConfirm").disabled = false; }
  };
  for (const name of ["input", "change"]) document.addEventListener(name, event => {
    if (!event.target.closest(".local-profiles, .profile-quick, #profileDialog")) schedule();
  }, true);
  document.addEventListener("workspace-rendered", schedule);
  document.addEventListener("workspace-before-sample", () => { if (ready) void save().catch(() => {}); });
  document.addEventListener("visibilitychange", () => { if (document.hidden && dirty && !state.sample.active) void save().catch(() => {}); });
  window.addEventListener("beforeunload", event => { if (dirty) { event.preventDefault(); event.returnValue = ""; } });
}

import { askPlanAssistant, el, listCaseVersions, maxStage, requestPlanGeneration, savePlanVersion, state } from "./state.js";
import { canonicalScanSources, demoInitialOffsets, syntheticCrowdingRows } from "./demo.js";
import { recenterViewer, renderAll, renderAvailability, renderChat, renderGeneration, renderVersions, setDimension, zoomViewer } from "./render.js";
import { planJson } from "./plan.js";
import { clearUploadedFiles, restoreUploadedFiles, saveUploadedFiles } from "./storage.js";
import { closestDatasetTarget } from "./core.js";

const savedTheme = localStorage.getItem("orthoplan-theme");
if (savedTheme === "dark") state.theme = "dark";

el("themeToggle").addEventListener("click", () => {
  state.theme = state.theme === "dark" ? "light" : "dark";
  localStorage.setItem("orthoplan-theme", state.theme);
  renderAll();
});

document.querySelectorAll(".mode-choice").forEach((button) => {
  button.addEventListener("click", () => {
    state.userMode = button.dataset.userMode;
    state.activeStep = "upload";
    document.querySelectorAll(".mode-choice").forEach((item) => item.classList.remove("is-active"));
    button.classList.add("is-active");
    renderAll();
  });
});

document.querySelectorAll(".step").forEach((button) => {
  button.addEventListener("click", () => {
    goToStep(button.dataset.step);
    renderAll();
  });
});

document.querySelectorAll(".mode").forEach((button) => {
  button.addEventListener("click", () => {
    state.view = button.dataset.view;
    document.querySelectorAll(".mode").forEach((item) => item.classList.remove("is-active"));
    button.classList.add("is-active");
    renderAll();
  });
});

document.querySelectorAll(".dim").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".dim").forEach((item) => item.classList.remove("is-active"));
    button.classList.add("is-active");
    setDimension(button.dataset.dim);
  });
});

el("stlFile").addEventListener("change", async (event) => {
  await setUploadedFiles(Array.from(event.target.files || []));
});

el("simpleStlFile").addEventListener("change", async (event) => {
  state.demoInitialOffsets = {};
  await setUploadedFiles(Array.from(event.target.files || []));
});

el("landmarksFile").addEventListener("change", async (event) => {
  const file = (event.target.files || [])[0];
  if (!file) return;
  try {
    const parsed = JSON.parse(await file.text());
    const count = Array.isArray(parsed?.landmarks) ? parsed.landmarks.length : 0;
    if (!count) throw new Error("no \"landmarks\" array found");
    state.generation.landmarks = parsed;
    state.generation.landmarksStatus = `Imported ${count} landmark(s) from ${file.name}. Generation will be landmark-derived.`;
  } catch (error) {
    state.generation.landmarks = null;
    state.generation.landmarksStatus = `Could not read landmarks: ${error.message}`;
  }
  renderGeneration();
});

document.body.addEventListener("input", (event) => {
  const target = event.target;
  if (target.dataset.availability) {
    state.availability[target.dataset.availability] = target.checked;
  }
  if (target.dataset.row) {
    const row = state.rows[Number(target.dataset.row)];
    const field = target.dataset.field;
    if (field === "tooth") {
      row[field] = target.value;
    } else {
      const num = Number(target.value);
      row[field] = Number.isFinite(num) ? num : 0;
    }
  }
  if (target.dataset.iprContact) {
    const value = Number(target.value);
    if (Number.isFinite(value) && value > 0) {
      state.clinicalControls.iprContacts[target.dataset.iprContact] = value;
    } else {
      delete state.clinicalControls.iprContacts[target.dataset.iprContact];
    }
  }
  if (target.id === "simpleGoal") state.simpleGoal = target.value;
  if (target.id === "simpleAcknowledged") state.simpleAcknowledged = target.checked;
  if (target.id === "chatProvider") state.chat.provider = target.value;
  if (target.id === "chatModel") state.chat.model = target.value;
  if (target.id === "chatScope") state.chat.contextScope = target.value;
  if (target.id === "chatInput") state.chat.input = target.value;
  if (target.id === "chatApiKey") state.chat.apiKeyPresent = Boolean(target.value.trim());
  if (target.id === "agentAccessEnabled") state.chat.agentAccessEnabled = target.checked;
  if (target.id === "generationAck") state.generation.acknowledged = target.checked;
  if (target.id === "generationNotes") state.generation.notes = target.value;
  if (target.id === "scanArchFilter") state.scanArchFilter = target.value;
  if (target.id === "glossarySearch") filterGlossary(target.value);
  if (target.id === "versionNote") state.versions.note = target.value;
  if (target.id === "agentEndpoint") state.chat.agentEndpoint = target.value;
  if (target.id === "printEnabled") state.printExport.enabled = target.checked;
  if (target.id === "printFormat") state.printExport.export_format = target.value;
  if (target.id === "printEmail") state.printExport.delivery_email = target.value;
  if (target.id === "modelMaterial") state.printExport.model_material = target.value;
  if (target.id === "thermoformingMaterial") state.printExport.thermoforming_material = target.value;
  if (target.id === "printSafety") state.printExport.safety_acknowledged = target.checked;
  renderAll();
});

document.body.addEventListener("click", (event) => {
  const target = event.target;
  const button = target.closest?.("button");
  const canonicalTarget = closestDatasetTarget(target, "canonicalMonths");
  const stepTarget = closestDatasetTarget(target, "stepTarget");
  const journeyTarget = closestDatasetTarget(target, "journeyStep");
  const removeUploadTarget = closestDatasetTarget(target, "removeUpload");
  const clearUploadsTarget = closestDatasetTarget(target, "clearUploads");
  const detailModeTarget = closestDatasetTarget(target, "detailMode");
  const restoreVersionTarget = closestDatasetTarget(target, "restoreVersion");
  const removeRowTarget = closestDatasetTarget(target, "remove");

  if (button?.id === "addStage") {
    state.rows.push({
      stage: maxStage() + 1,
      tooth: "21",
      x: 0.1,
      y: 0,
      z: 0,
      tip: 0,
      torque: 0,
      rotation: 0,
    });
    renderAll();
  }
  if (button?.id === "loadDemo") {
    loadSyntheticDemo();
  }
  if (canonicalTarget) {
    loadCanonicalCase(Number(canonicalTarget.dataset.canonicalMonths));
  }
  if (stepTarget) {
    goToStep(stepTarget.dataset.stepTarget);
    renderAll();
  }
  if (journeyTarget) {
    goToStep(journeyTarget.dataset.journeyStep);
    renderAll();
  }
  if (removeUploadTarget) {
    const nextFiles = state.files.filter((_, index) => index !== Number(removeUploadTarget.dataset.removeUpload));
    setUploadedFiles(nextFiles);
  }
  if (clearUploadsTarget) {
    setUploadedFiles([]);
  }
  if (detailModeTarget) {
    state.detailMode[detailModeTarget.dataset.detailMode] = detailModeTarget.dataset.detailValue;
    renderAll();
  }
  if (button?.id === "simpleReview") {
    if (!state.simpleAcknowledged) return;
    state.activeStep = "review";
    state.view = "overlay";
    renderAll();
  }
  if (button?.id === "uploadNext") {
    goToStep("availability");
    renderAll();
  }
  if (button?.id === "simpleNext") {
    goToStep("review");
    state.view = "overlay";
    renderAll();
  }
  if (button?.id === "downloadPlan") downloadJson("orthoplan-plan.json", planJson());
  if (button?.id === "downloadEvaluation" && state.lastEval) downloadJson("orthoplan-evaluation.json", state.lastEval);
  if (button?.id === "downloadPrintMetadata" && state.lastEval?.print_export) {
    downloadJson("orthoplan-print-metadata.json", state.lastEval.print_export);
  }
  if (button?.id === "sendChat") {
    sendChatMessage();
  }
  if (button?.id === "generatePlan") {
    generatePlan();
  }
  if (button?.id === "saveVersion") {
    saveVersion();
  }
  if (restoreVersionTarget) {
    const version = state.versions.list[Number(restoreVersionTarget.dataset.restoreVersion)];
    if (version?.snapshot) restorePlan(version.snapshot);
  }
  if (button?.id === "zoomIn") zoomViewer(0.83);
  if (button?.id === "zoomOut") zoomViewer(1.2);
  if (button?.id === "zoomReset") recenterViewer();
  if (removeRowTarget) {
    state.rows.splice(Number(removeRowTarget.dataset.remove), 1);
    renderAll();
  }
});

function uploadLabel(files, emptyLabel) {
  if (!files.length) return emptyLabel;
  if (files.length === 1) return files[0].name;
  return `${files.length} STL files selected`;
}

function goToStep(step) {
  if (step === "sample") {
    loadCanonicalCase(4, { activeStep: "sample" });
    return;
  }
  state.activeStep = step;
}

async function setUploadedFiles(files) {
  const stlFiles = files.filter((file) => file?.name?.toLowerCase().endsWith(".stl"));
  state.files = stlFiles;
  state.file = stlFiles[0] || null;
  state.scanSources = [];
  state.useDemoMeshes = false;
  state.scanArchFilter = "both";
  state.sampleStatus = stlFiles.length
    ? "Uploaded STL scan layer · movement preview is schematic until segmented per-tooth meshes are available."
    : "";
  updateUploadLabels();
  if (stlFiles.length) {
    state.uploadStorageStatus = "Saving STL files locally in this browser...";
    try {
      await saveUploadedFiles(stlFiles);
      state.uploadStorageStatus = "Saved locally in this browser. Use Clear All or x to remove.";
    } catch (error) {
      state.uploadStorageStatus = `Loaded for this session only; browser storage failed: ${error.message}`;
    }
  } else {
    await clearUploadedFiles().catch(() => {});
    state.uploadStorageStatus = files.length ? "No STL files were selected." : "";
    el("stlFile").value = "";
    el("simpleStlFile").value = "";
  }
  renderAll();
}

function updateUploadLabels() {
  el("uploadLabel").textContent = uploadLabel(state.files, "Choose STL files");
  el("simpleUploadLabel").textContent = uploadLabel(state.files, "Choose your STL files");
}

function downloadJson(filename, value) {
  const blob = new Blob([JSON.stringify(value, null, 2)], { type: "application/json" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  document.body.append(link);
  link.click();
  const href = link.href;
  link.remove();
  URL.revokeObjectURL(href);
}

function loadSyntheticDemo() {
  state.userMode = "simple";
  state.simpleAcknowledged = true;
  state.simpleGoal = "crowding";
  state.demoInitialOffsets = demoInitialOffsets;
  state.useDemoMeshes = true;
  state.sampleStatus = "Educational demo · bundled tooth meshes · simulated crowding movement.";
  state.rows = syntheticCrowdingRows(12);
  state.files = [];
  state.scanSources = [];
  state.file = null;
  state.uploadStorageStatus = "";
  clearUploadedFiles().catch(() => {});
  updateUploadLabels();
  state.view = "overlay";
  state.activeStep = "review";
  el("planTitle").value = "Educational crowding demo";
  el("planId").value = "synthetic-crowding-demo";
  el("wearInterval").value = "30";
  el("exaggeration").value = "12";
  el("simpleGoal").value = "crowding";
  el("simpleAcknowledged").checked = true;
  renderAll();
}

function loadCanonicalCase(months, options) {
  const stageCount = months === 4 ? 4 : (months === 6 ? 6 : 12);
  state.simpleAcknowledged = true;
  state.simpleGoal = "crowding";
  state.demoInitialOffsets = demoInitialOffsets;
  state.useDemoMeshes = true;
  state.sampleStatus =
    `Sample test case · real upper/lower OrthoCAD STL scan layer · simulated ${months}-month tooth movement.`;
  state.files = [];
  state.file = null;
  state.uploadStorageStatus = "";
  state.scanArchFilter = "both";
  state.scanRenderStatus = "Loading built-in upper/lower OrthoCAD STL scan layer...";
  clearUploadedFiles().catch(() => {});
  state.scanSources = canonicalScanSources;
  state.rows = syntheticCrowdingRows(stageCount, { includeBaseline: true });
  state.view = "overlay";
  state.activeStep = options?.activeStep || "sample";
  state.availability.intraoral_scan = true;
  state.availability.occlusion_scan = true;
  state.availability.segmented_teeth = false;
  el("planTitle").value = `Canonical OrthoCAD simulated ${months}-month progression`;
  el("planId").value = `canonical-orthocad-${months}-month`;
  el("wearInterval").value = "30";
  el("exaggeration").value = "12";
  el("scanUnits").value = "mm";
  el("scanArch").value = "";
  el("simpleGoal").value = "crowding";
  el("simpleAcknowledged").checked = true;
  el("uploadLabel").textContent = "Canonical upper + lower OrthoCAD STLs";
  el("simpleUploadLabel").textContent = "Canonical upper + lower OrthoCAD STLs";
  renderAvailability();
  renderAll();
}

async function restoreStoredUploads() {
  try {
    const files = await restoreUploadedFiles();
    if (!files.length) return;
    state.files = files;
    state.file = files[0];
    state.scanSources = [];
    state.useDemoMeshes = false;
    state.uploadStorageStatus = "Restored saved STL files from this browser.";
    updateUploadLabels();
    renderAll();
  } catch {
    // Browser storage is a convenience; a failed restore should never block use.
  }
}

async function sendChatMessage() {
  const message = state.chat.input.trim();
  if (!message || state.chat.busy) return;
  state.chat.busy = true;
  state.chat.status = "Reviewing the scoped plan context...";
  state.chat.messages.push({ role: "user", content: message });
  el("chatInput").value = "";
  state.chat.input = "";
  renderChat();
  try {
    // The API key is read straight from the DOM at send time so it is never
    // held in app state or persisted - only transmitted on an explicit "Ask AI".
    const apiKey = el("chatApiKey").value.trim();
    const result = await askPlanAssistant({
      plan: planJson(),
      message,
      provider: state.chat.provider,
      model: state.chat.model,
      context_scope: state.chat.contextScope,
      api_key: apiKey || undefined,
      endpoint: state.chat.agentEndpoint.trim() || undefined,
      share_acknowledged: state.chat.agentAccessEnabled,
    });
    if (result.ok === false) {
      state.chat.messages.push({
        role: "assistant",
        content: (result.errors || ["AI chat is not available."]).join(" "),
      });
      state.chat.status = "Connector unavailable";
    } else {
      const assistant = [...result.session.messages].reverse().find((item) => item.role === "assistant");
      state.chat.messages.push({
        role: "assistant",
        content: assistant?.content || "No answer returned.",
      });
      state.chat.status = `${result.session.connector.label} · ${result.session.context_scope.name}`;
    }
  } catch (error) {
    state.chat.messages.push({ role: "assistant", content: error.message });
    state.chat.status = "Chat request failed";
  } finally {
    state.chat.busy = false;
    renderChat();
  }
}

function rowsFromPlan(plan) {
  const rows = [];
  for (const stage of plan.stages || []) {
    for (const d of stage.deltas || []) {
      rows.push({
        stage: stage.index,
        tooth: d.tooth.value,
        x: d.translate_x_mm,
        y: d.translate_y_mm,
        z: d.translate_z_mm,
        tip: d.rotate_tip_deg,
        torque: d.rotate_torque_deg,
        rotation: d.rotate_rotation_deg,
      });
    }
  }
  return rows;
}

async function generatePlan() {
  if (state.generation.busy) return;
  state.generation.busy = true;
  state.generation.status = "Reviewing scan, generating, and orchestrating checks...";
  renderGeneration();
  try {
    // The API key is read from the DOM only at request time (never persisted),
    // matching the chat layer. The external-agent acknowledgement opts into the
    // optional model review step; without it the pipeline runs fully offline.
    const apiKey = el("chatApiKey").value.trim();
    const result = await requestPlanGeneration({
      plan: planJson(),
      landmarks: state.generation.landmarks || undefined,
      acknowledge_educational: state.generation.acknowledged,
      notes: state.generation.notes.trim() || undefined,
      provider: state.chat.provider,
      model: state.chat.model,
      api_key: apiKey || undefined,
      endpoint: state.chat.agentEndpoint.trim() || undefined,
      share_acknowledged: state.chat.agentAccessEnabled,
    });
    if (result.ok === false) {
      state.generation.result = null;
      state.generation.status = (result.errors || ["Generation failed."]).join("; ");
    } else {
      state.generation.result = result;
      state.generation.status = `source: ${result.source} · ${result.correctness.verdict}`;
      // Load generated staging into the editable rows so the existing review,
      // timeline, and 3D pipeline visualize it - the UI never re-stages itself.
      if (result.plan?.stages?.length) {
        state.rows = rowsFromPlan(result.plan);
        state.activeStep = "review";
        state.view = "overlay";
      }
    }
  } catch (error) {
    state.generation.result = null;
    state.generation.status = error.message;
  } finally {
    state.generation.busy = false;
    renderAll();
  }
}

function filterGlossary(query) {
  const term = query.trim().toLowerCase();
  const entries = document.querySelectorAll(".glossary dl > div");
  let visible = 0;
  entries.forEach((entry) => {
    const match = !term || entry.textContent.toLowerCase().includes(term);
    entry.hidden = !match;
    if (match) visible += 1;
  });
  el("glossaryEmpty").hidden = visible !== 0;
}

async function loadVersions() {
  const caseId = el("planId").value.trim();
  if (!caseId) return;
  try {
    const result = await listCaseVersions(caseId);
    state.versions.list = result.ok ? result.versions : [];
  } catch {
    state.versions.list = [];
  }
  renderVersions();
}

async function saveVersion() {
  if (state.versions.busy) return;
  state.versions.busy = true;
  state.versions.status = "Saving version...";
  renderVersions();
  try {
    const result = await savePlanVersion({
      plan: planJson(),
      case_id: el("planId").value.trim() || undefined,
      note: state.versions.note.trim() || undefined,
    });
    if (result.ok === false) {
      state.versions.status = (result.errors || ["Save failed."]).join("; ");
    } else {
      state.versions.status = `Saved ${result.version.version_id}`;
      state.versions.note = "";
      el("versionNote").value = "";
      await loadVersions();
    }
  } catch (error) {
    state.versions.status = error.message;
  } finally {
    state.versions.busy = false;
    renderVersions();
  }
}

function restorePlan(snapshot) {
  el("planId").value = snapshot.id || "";
  el("planTitle").value = snapshot.title || "";
  const wear = snapshot.settings?.timeline?.wear_interval_days;
  if (wear) el("wearInterval").value = wear;
  const caps = snapshot.settings?.movement_caps?.default;
  if (caps) {
    el("capLinear").value = caps.linear_mm;
    el("capAngular").value = caps.angular_deg;
    el("capRotation").value = caps.rotation_deg;
    el("capVertical").value = caps.intrusion_extrusion_mm;
  }
  if (snapshot.data) state.availability = { ...state.availability, ...snapshot.data };
  state.rows = rowsFromPlan(snapshot);
  state.activeStep = "review";
  state.view = "overlay";
  state.versions.status = `Restored ${snapshot.id || "plan"} into the editor`;
  renderAvailability();
  renderAll();
}

renderAvailability();
renderAll();
restoreStoredUploads();
loadVersions();

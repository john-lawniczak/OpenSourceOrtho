import { askPlanAssistant, el, maxStage, requestPlanGeneration, state } from "./state.js";
import { canonicalScanSources, demoInitialOffsets, syntheticCrowdingRows } from "./demo.js";
import { recenterViewer, renderAll, renderAvailability, renderChat, renderGeneration, setDimension, zoomViewer } from "./render.js";
import { planJson } from "./plan.js";
import { clearUploadedFiles, restoreUploadedFiles, saveUploadedFiles } from "./storage.js";

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
    state.activeStep = button.dataset.step;
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
  if (target.id === "addStage") {
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
  if (target.id === "loadDemo") {
    loadSyntheticDemo();
  }
  if (target.dataset.canonicalMonths) {
    loadCanonicalCase(Number(target.dataset.canonicalMonths));
  }
  if (target.dataset.stepTarget) {
    state.activeStep = target.dataset.stepTarget;
    renderAll();
  }
  if (target.dataset.journeyStep) {
    state.activeStep = target.dataset.journeyStep;
    renderAll();
  }
  if (target.dataset.removeUpload) {
    const nextFiles = state.files.filter((_, index) => index !== Number(target.dataset.removeUpload));
    setUploadedFiles(nextFiles);
  }
  if (target.dataset.clearUploads) {
    setUploadedFiles([]);
  }
  if (target.id === "simpleReview") {
    if (!state.simpleAcknowledged) return;
    state.activeStep = "review";
    state.view = "overlay";
    renderAll();
  }
  if (target.id === "uploadNext") {
    state.activeStep = "availability";
    renderAll();
  }
  if (target.id === "simpleNext") {
    state.activeStep = "review";
    state.view = "overlay";
    renderAll();
  }
  if (target.id === "downloadPlan") downloadJson("orthoplan-plan.json", planJson());
  if (target.id === "downloadEvaluation" && state.lastEval) downloadJson("orthoplan-evaluation.json", state.lastEval);
  if (target.id === "downloadPrintMetadata" && state.lastEval?.print_export) {
    downloadJson("orthoplan-print-metadata.json", state.lastEval.print_export);
  }
  if (target.id === "sendChat") {
    sendChatMessage();
  }
  if (target.id === "generatePlan") {
    generatePlan();
  }
  if (target.id === "zoomIn") zoomViewer(0.83);
  if (target.id === "zoomOut") zoomViewer(1.2);
  if (target.id === "zoomReset") recenterViewer();
  if (target.dataset.remove) {
    state.rows.splice(Number(target.dataset.remove), 1);
    renderAll();
  }
});

function uploadLabel(files, emptyLabel) {
  if (!files.length) return emptyLabel;
  if (files.length === 1) return files[0].name;
  return `${files.length} STL files selected`;
}

async function setUploadedFiles(files) {
  const stlFiles = files.filter((file) => file?.name?.toLowerCase().endsWith(".stl"));
  state.files = stlFiles;
  state.file = stlFiles[0] || null;
  state.scanSources = [];
  state.useDemoMeshes = false;
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

function loadCanonicalCase(months) {
  const stageCount = months === 6 ? 6 : 12;
  state.simpleAcknowledged = true;
  state.simpleGoal = "crowding";
  state.demoInitialOffsets = demoInitialOffsets;
  state.useDemoMeshes = true;
  state.files = [];
  state.file = null;
  state.uploadStorageStatus = "";
  clearUploadedFiles().catch(() => {});
  state.scanSources = canonicalScanSources;
  state.rows = syntheticCrowdingRows(stageCount);
  state.view = "overlay";
  state.activeStep = "review";
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
      acknowledge_educational: state.generation.acknowledged,
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

renderAvailability();
renderAll();
restoreStoredUploads();

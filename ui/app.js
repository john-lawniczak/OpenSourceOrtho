import { askPlanAssistant, el, listCaseVersions, maxStage, requestPlanGeneration, savePlanVersion, state } from "./state.js";
import { demoInitialOffsets, syntheticCrowdingRows } from "./demo.js";
import { recenterViewer, renderAll, renderAvailability, renderChat, renderGeneration, renderVersions, requestViewerRefit, setDimension, zoomViewer } from "./render.js";
import { planJson } from "./plan.js";
import {
  clearUploadedFiles,
  restoreSegmentationReview,
  restoreUploadedFiles,
  saveSegmentationReview,
  saveUploadedFiles,
} from "./storage.js";
import { closestDatasetTarget } from "./core.js";
import {
  downloadPrintArtifact,
  goGuided,
  guidedBack,
  guidedNext,
  runPrintPackage,
  setWearInterval,
  toggleExcludedTooth,
} from "./guided.js";
import { enterSample, exitSample, sampleActive } from "./sample.js";
import { applySegmentation, proposeSegmentation, setSegmentInclude, setSegmentToothEdit } from "./segment.js";
import { NUDGE_STEP_MM, clearTarget, nudgeTarget, scaleConfirmed } from "./manual_edit.js";

const savedTheme = localStorage.getItem("orthoplan-theme");
if (savedTheme === "dark") state.theme = "dark";

el("themeToggle").addEventListener("click", () => {
  state.theme = state.theme === "dark" ? "light" : "dark";
  localStorage.setItem("orthoplan-theme", state.theme);
  renderAll();
});

function setUserMode(mode) {
  state.userMode = mode;
  if (mode === "simple" && !state.guided.step) state.guided.step = "upload";
  renderAll();
  maybeRecenterPreview();
}

// The 3D viewer may be sized while its host is hidden (1x1) or framed for a
// previous scene. When it becomes visible - or moves between guided step hosts
// (teeth, details, preview all now embed it) - request a one-shot re-frame that
// runs after the next evaluation populates the scene at its real size.
const VIEWER_GUIDED_STEPS = new Set(["plan", "details", "preview"]);

function maybeRecenterPreview() {
  if (state.userMode === "simple" && VIEWER_GUIDED_STEPS.has(state.guided.step)) {
    requestViewerRefit();
  }
}

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
  // Segmentation edits update state in place and deliberately do NOT trigger a
  // full re-render, so typing a corrected tooth number never loses input focus.
  if (target.dataset.segmentTooth) {
    setSegmentToothEdit(target.dataset.segmentTooth, target.value);
    persistSegmentationReview();
    return;
  }
  if (target.dataset.segmentInclude) {
    setSegmentInclude(target.dataset.segmentInclude, target.checked);
    persistSegmentationReview();
    return;
  }
  if (target.id === "segmentMissingTeeth") {
    state.segmentation.missingTeeth = target.value;
    persistSegmentationReview();
  }
  if (target.dataset.availability) {
    state.availability[target.dataset.availability] = target.checked;
  }
  if (target.dataset.guidedTooth) {
    toggleExcludedTooth(target.dataset.guidedTooth);
  }
  if (target.id === "guidedExaggeration") {
    // The guided slider mirrors the technician numeric exaggeration field so the
    // viewer reads one source of truth.
    el("exaggeration").value = target.value;
    el("guidedExaggerationValue").textContent = `×${target.value}`;
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
  const stepTarget = closestDatasetTarget(target, "stepTarget");
  const infoBackTarget = closestDatasetTarget(target, "infoBack");
  const journeyTarget = closestDatasetTarget(target, "journeyStep");
  const removeUploadTarget = closestDatasetTarget(target, "removeUpload");
  const clearUploadsTarget = closestDatasetTarget(target, "clearUploads");
  const detailModeTarget = closestDatasetTarget(target, "detailMode");
  const restoreVersionTarget = closestDatasetTarget(target, "restoreVersion");
  const removeRowTarget = closestDatasetTarget(target, "remove");
  const userModeTarget = closestDatasetTarget(target, "userMode");
  const guidedStepTarget = closestDatasetTarget(target, "gstepNav");
  const printArtifactTarget = closestDatasetTarget(target, "printArtifact");
  const wearTarget = closestDatasetTarget(target, "wear");

  if (wearTarget) {
    setWearInterval(Number(wearTarget.dataset.wear));
    renderAll();
    return;
  }
  if (userModeTarget) {
    setUserMode(userModeTarget.dataset.userMode);
    return;
  }
  if (guidedStepTarget) {
    goGuided(guidedStepTarget.dataset.gstepNav);
    renderAll();
    maybeRecenterPreview();
    return;
  }
  if (button?.id === "guidedBack") {
    guidedBack();
    renderAll();
    maybeRecenterPreview();
  }
  if (button?.id === "guidedNext") {
    guidedNext();
    renderAll();
    maybeRecenterPreview();
  }
  if (button?.id === "sampleLaunch") {
    // The sidebar launcher toggles the sample so it can be exited from either
    // Guided or Technician view, wherever the user has navigated.
    if (sampleActive()) {
      exitSample();
    } else {
      enterSample();
      requestViewerRefit();
    }
    renderAll();
  }
  if (button?.id === "sampleExit") {
    exitSample();
    renderAll();
  }
  if (button?.id === "guidedBuild") {
    generatePlan();
    renderAll();
  }
  if (button?.id === "toothLabelToggle") {
    state.showToothLabels = !state.showToothLabels;
    renderAll();
  }
  if (button?.id === "proposeSegment" || button?.id === "reanchorSegment") {
    // Re-anchor re-runs the proposal with the current "missing teeth" so the FDI
    // labels line up around the gap; same code path as a fresh proposal.
    proposeSegmentation().then(() => {
      persistSegmentationReview();
      renderAll();
    });
    renderAll();
  }
  if (button?.id === "applySegment") {
    applySegmentation();
    persistSegmentationReview();
    renderAll();
  }
  if (button?.id === "guidedPrint") {
    runPrintPackage();
  }
  if (printArtifactTarget) {
    downloadPrintArtifact(printArtifactTarget.dataset.printArtifact);
  }

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
  if (button?.dataset.manualNudge) {
    applyManualNudge(button.dataset.manualNudge);
  }
  if (button?.id === "manualTargetReset") {
    const tooth = state.manualEdit.selectedTooth;
    if (tooth) {
      state.rows = clearTarget(state.rows, tooth);
      renderAll();
    }
  }
  if (button?.id === "manualClearSelection") {
    state.manualEdit.selectedTooth = null;
    renderAll();
  }
  if (button?.id === "loadDemo") {
    loadSyntheticDemo();
  }
  if (stepTarget) {
    goToStep(stepTarget.dataset.stepTarget);
    renderAll();
  }
  if (infoBackTarget) {
    goToStep(state.returnStep || "upload");
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
  if (button?.id === "uploadNext") {
    goToStep("availability");
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

// Reference panels (Key Terms / Tooth Map, Imaging & Photos guide) are reachable
// from the sidebar in BOTH guided and technician mode. They are not workflow
// steps, so opening one remembers where to return to.
const INFO_STEPS = ["toothmap", "glossary", "photos"];

function goToStep(step) {
  if (INFO_STEPS.includes(step) && !INFO_STEPS.includes(state.activeStep)) {
    state.returnStep = state.activeStep;
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

// Apply one planar nudge to the selected tooth's authored target. `direction` is
// "x-" | "x+" | "y-" | "y+". Gated on confirmed scan units so a mm nudge is
// never authored against unverified scale. Movement itself is recomputed by the
// engine on the next evaluation (the UI never computes poses).
function applyManualNudge(direction) {
  const tooth = state.manualEdit.selectedTooth;
  if (!tooth || !scaleConfirmed(state.scanUnits)) return;
  const axis = direction[0]; // "x" or "y"
  const delta = direction.endsWith("-") ? -NUDGE_STEP_MM : NUDGE_STEP_MM;
  state.rows = nudgeTarget(state.rows, tooth, axis, delta);
  renderAll();
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

// Persist the segmentation review (proposal, corrections, marked gaps, applied
// fragment) for the current plan id so it survives a page reload.
function persistSegmentationReview() {
  const planId = el("planId").value.trim();
  if (!planId) return;
  const { proposal, edits, applied, missingTeeth } = state.segmentation;
  saveSegmentationReview(planId, { proposal, edits, applied, missingTeeth });
}

// Rehydrate a saved segmentation review for a plan id (on load or version
// restore). Returns true when something was restored.
function loadSegmentationReview(planId) {
  const review = restoreSegmentationReview(planId);
  if (!review) return false;
  state.segmentation.proposal = review.proposal || null;
  state.segmentation.edits = review.edits || {};
  state.segmentation.applied = review.applied || null;
  state.segmentation.missingTeeth = review.missingTeeth || "";
  const missingInput = el("segmentMissingTeeth");
  if (missingInput) missingInput.value = state.segmentation.missingTeeth;
  return true;
}

function restoreStoredSegmentation() {
  if (loadSegmentationReview(el("planId").value.trim())) {
    if (state.segmentation.proposal) {
      state.segmentation.status = "Restored your earlier segmentation review from this browser.";
    }
    renderAll();
  }
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
  // Bring back this plan's segmentation review draft (corrections, marked gaps),
  // then let the saved snapshot's applied per-tooth meshes win - they are the
  // authoritative segmentation for the version being restored.
  loadSegmentationReview(snapshot.id || "");
  if (snapshot.mesh_assets?.length || snapshot.tooth_meshes?.length) {
    state.segmentation.applied = {
      mesh_assets: snapshot.mesh_assets || [],
      tooth_meshes: snapshot.tooth_meshes || [],
    };
  }
  persistSegmentationReview();
  state.activeStep = "review";
  state.view = "overlay";
  state.versions.status = `Restored ${snapshot.id || "plan"} into the editor`;
  renderAvailability();
  renderAll();
}

renderAvailability();
renderAll();
restoreStoredUploads();
restoreStoredSegmentation();
loadVersions();

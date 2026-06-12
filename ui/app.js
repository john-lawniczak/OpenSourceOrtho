import { askPlanAssistant, el, listCaseVersions, loadAiConnectors, maxStage, requestCaseReview, requestCbctAnatomyProposal, requestCbctAnatomyReview, savePlanVersion, state, streamPlanAssistant, uploadCaseRecord, uploadStlFile } from "./state.js";
import { demoInitialOffsets, syntheticCrowdingRows } from "./demo.js";
import { recenterViewer, renderAll, renderAvailability, renderChat, renderGeneration, renderStagePreview, renderVersions, requestViewerRefit, setDimension, zoomViewer } from "./render.js";
import { planJson } from "./plan.js";
import { qrSvg } from "./qrcode.js";
import {
  clearUploadedFiles,
  restoreSegmentationReview,
  restoreUploadedFiles,
  saveSegmentationReview,
  saveUploadedFiles,
} from "./storage.js";
import { closestDatasetTarget, inferArchFromName, rowsFromPlan } from "./core.js";
import { generatePlan } from "./generation.js";
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
import { registrationActionable, requestProximity } from "./proximity.js";
import { NUDGE_STEP_MM, clearTarget, nudgeTarget, scaleConfirmed } from "./manual_edit.js";

const savedTheme = localStorage.getItem("orthoplan-theme");
if (savedTheme === "dark") state.theme = "dark";

loadAiConnectors().then((result) => {
  if (result.ok && Array.isArray(result.connectors) && result.connectors.length) {
    state.chat.connectors = result.connectors;
    state.chat.modelByProvider = Object.fromEntries(
      result.connectors.map((connector) => [
        connector.kind,
        state.chat.modelByProvider[connector.kind] || connector.model || connector.models?.[0],
      ]),
    );
    renderChat();
  }
}).catch(() => {
  state.chat.status = "Local helper ready";
});

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
const GUIDED_STAGE_CONTEXT = {
  upload: {
    label: "Guided step 1: Upload",
    purpose: "Collect STL scan files and confirm the educational-use acknowledgement.",
  },
  plan: {
    label: "Guided step 2: Teeth and time",
    purpose: "Generate a starter staged plan, choose which teeth move, and set tray wear interval.",
  },
  details: {
    label: "Guided step 3: Details",
    purpose: "Adjust preview-only movement exaggeration and inspect how movement appears.",
  },
  review: {
    label: "Guided step 4: Review",
    purpose: "Summarize tray count, projected duration, and moved teeth in plain language.",
  },
  preview: {
    label: "Guided step 5: 3D preview",
    purpose: "Scrub through the staged movement timeline in the 3D viewer.",
  },
  print: {
    label: "Guided step 6: Print / send",
    purpose: "Prepare downloadable print handoff artifacts after review.",
  },
};
const TECH_STAGE_CONTEXT = {
  upload: {
    label: "Technician step: Upload STL",
    purpose: "Add upper/lower STL scans and set scan units and arch metadata.",
  },
  availability: {
    label: "Technician step: Data availability",
    purpose: "Declare available records so data gaps and acquisition guidance are accurate.",
  },
  settings: {
    label: "Technician step: Movement settings",
    purpose: "Set movement caps, print metadata, and clinical controls such as fixed teeth, attachments, exclusions, and IPR.",
  },
  stages: {
    label: "Technician step: Stage builder",
    purpose: "Author per-tooth staged movement rows using FDI tooth IDs, millimeters, and degrees.",
  },
  review: {
    label: "Technician step: Review",
    purpose: "Inspect the visual timeline, findings, generate-plan output, segmentation, versions, downloads, and plan JSON.",
  },
  toothmap: {
    label: "Reference: Tooth map",
    purpose: "Explain FDI and Universal numbering for identifying teeth.",
  },
  glossary: {
    label: "Reference: Glossary",
    purpose: "Define dental and planning terms in plain language.",
  },
  photos: {
    label: "Reference: Imaging and photos guide",
    purpose: "Explain what records help the engine and what each record adds.",
  },
};

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

el("dicomFile").addEventListener("change", async (event) => {
  await addCaseRecordFiles(Array.from(event.target.files || []), { kind: "cbct", modality: "CBCT/DICOM" });
  event.target.value = "";
});

el("attachmentFile").addEventListener("change", async (event) => {
  await addCaseRecordFiles(Array.from(event.target.files || []));
  event.target.value = "";
});

el("cbctMaskFile").addEventListener("change", async (event) => {
  await loadCbctMaskFile((event.target.files || [])[0]);
  event.target.value = "";
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
  if (target.id === "chatProvider") {
    state.chat.provider = target.value;
    state.chat.model = state.chat.modelByProvider[state.chat.provider] || defaultModelForProvider(state.chat.provider);
  }
  if (target.id === "chatModel") {
    state.chat.model = target.value === "__custom__"
      ? el("chatCustomModel").value.trim() || "custom-model"
      : target.value;
    if (state.chat.model) state.chat.modelByProvider[state.chat.provider] = state.chat.model;
  }
  if (target.id === "chatCustomModel") {
    state.chat.model = target.value.trim();
    if (state.chat.model) state.chat.modelByProvider[state.chat.provider] = state.chat.model;
  }
  if (target.id === "chatInput") state.chat.input = target.value;
  if (target.id === "chatApiKey") state.chat.apiKeyPresent = Boolean(target.value.trim());
  if (target.id === "agentAccessEnabled") state.chat.agentAccessEnabled = target.checked;
  if (target.id === "generationAck") state.generation.acknowledged = target.checked;
  if (target.id === "generationNotes") state.generation.notes = target.value;
  if (target.id === "scanArchFilter") state.scanArchFilter = target.value;
  if (target.id === "stageSlider") {
    renderStagePreview();
    return;
  }
  if (target.id === "glossarySearch") filterGlossary(target.value);
  if (target.id === "versionNote") state.versions.note = target.value;
  if (target.id === "agentEndpoint") state.chat.agentEndpoint = target.value;
  if (target.id === "printEnabled") state.printExport.enabled = target.checked;
  if (target.id === "printFormat") state.printExport.export_format = target.value;
  if (target.id === "printEmail") state.printExport.delivery_email = target.value;
  if (target.id === "modelMaterial") state.printExport.model_material = target.value;
  if (target.id === "thermoformingMaterial") state.printExport.thermoforming_material = target.value;
  if (target.id === "printSafety") state.printExport.safety_acknowledged = target.checked;
  if (target.id === "alignerShellEnabled") state.printExport.aligner_shell_enabled = target.checked;
  if (target.id === "sheetThickness") state.printExport.sheet_thickness_mm = Number(target.value) || 0.6;
  if (target.id === "trimMargin") state.printExport.gingival_trim_margin_mm = Number(target.value);
  if (target.id === "cbctRegistrationAccepted") state.cbctWorkflow.registrationAccepted = target.checked;
  if (target.id === "cbctRegistrationRmse") state.cbctWorkflow.rmseMm = Number(target.value) || 0;
  if (target.id === "cbctRegistrationFitness") state.cbctWorkflow.fitness = Number(target.value) || 0;
  renderAll();
});

document.body.addEventListener("keydown", (event) => {
  if (event.target?.id !== "chatInput") return;
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendChatMessage();
  }
});

document.body.addEventListener("click", (event) => {
  const target = event.target;
  const button = target.closest?.("button");
  const stepTarget = closestDatasetTarget(target, "stepTarget");
  const infoBackTarget = closestDatasetTarget(target, "infoBack");
  const journeyTarget = closestDatasetTarget(target, "journeyStep");
  const removeUploadTarget = closestDatasetTarget(target, "removeUpload");
  const clearUploadsTarget = closestDatasetTarget(target, "clearUploads");
  const removeRecordTarget = closestDatasetTarget(target, "removeRecord");
  const detailModeTarget = closestDatasetTarget(target, "detailMode");
  const restoreVersionTarget = closestDatasetTarget(target, "restoreVersion");
  const removeRowTarget = closestDatasetTarget(target, "remove");
  const userModeTarget = closestDatasetTarget(target, "userMode");
  const guidedStepTarget = closestDatasetTarget(target, "gstepNav");
  const printArtifactTarget = closestDatasetTarget(target, "printArtifact");
  const wearTarget = closestDatasetTarget(target, "wear");
  const anatomyReviewTarget = closestDatasetTarget(target, "anatomyReview");

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
  if (button?.id === "guidedRebuild") {
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
  if (button?.id === "addRecordNote") {
    addNoteRecord();
    renderAll();
  }
  if (button?.id === "proposeCbctAnatomy") {
    proposeCbctAnatomy();
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
  if (button?.id === "manualTargetReset" || button?.id === "guidedTargetReset") {
    const tooth = state.manualEdit.selectedTooth;
    if (tooth) {
      pushManualUndo();
      state.rows = clearTarget(state.rows, tooth);
      renderAll();
    }
  }
  if (button?.id === "manualClearSelection" || button?.id === "guidedClearSelection") {
    state.manualEdit.selectedTooth = null;
    renderAll();
  }
  if (button?.id === "guidedEditUndo") {
    const previous = state.manualEdit.undoStack?.pop();
    if (previous) {
      state.rows = previous;
      renderAll();
    }
  }
  if (button?.dataset.guidedView) {
    state.view = button.dataset.guidedView;
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
  if (removeRecordTarget) {
    state.caseRecords = state.caseRecords.filter((record) => record.id !== removeRecordTarget.dataset.removeRecord);
    updateAvailabilityFromCaseRecords();
    renderAll();
  }
  if (anatomyReviewTarget) {
    applyAnatomyReview(
      anatomyReviewTarget.dataset.anatomyGroup,
      Number(anatomyReviewTarget.dataset.anatomyIndex),
      anatomyReviewTarget.dataset.anatomyReview,
    );
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
  if (button?.id === "exportCaseReview") {
    exportCaseReview();
  }
  if (button?.id === "sendChat") {
    sendChatMessage();
  }
  if (button?.id === "proximityToggle") {
    toggleProximity();
  }
  if (button?.id === "scaleToggle") {
    state.showScale = !state.showScale;
    renderAll();
  }
  if (button?.id === "registeredBiteToggle") {
    toggleRegisteredBite();
  }
  if (button?.id === "stagePlayToggle") {
    toggleStagePlayback();
  }
  if (button?.id === "toggleChatPanel" || button?.id === "chatReopenTab") {
    state.chat.collapsed = !state.chat.collapsed;
    renderChat();
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
  stopStagePlayback();
  const stlFiles = files.filter((file) => file?.name?.toLowerCase().endsWith(".stl"));
  state.files = stlFiles;
  state.file = stlFiles[0] || null;
  state.scanSources = [];
  state.useDemoMeshes = false;
  state.scanArchFilter = "both";
  // A new scan invalidates any prior segmentation: its per-tooth meshes live in
  // the OLD scan's coordinates, so leaving them applied would render stale crowns
  // misaligned over the new scan. Drop the proposal/applied fragment.
  state.segmentation = { busy: false, status: "", proposal: null, edits: {}, applied: null, missingTeeth: state.segmentation.missingTeeth };
  // A new scan also invalidates any bite-proximity overlay: it was computed for the
  // previous scan pair's coordinates and uploaded files cannot be read server-side.
  state.proximity = { enabled: false, busy: false, status: "", map: null, registration: null, registeredView: false };
  state.sampleStatus = stlFiles.length
    ? "Uploaded STL scan layer · movement preview is schematic until segmented per-tooth meshes are available."
    : "";
  updateUploadLabels();
  if (stlFiles.length) {
    state.uploadStorageStatus = "Saving STL files locally in this browser...";
    try {
      await saveUploadedFiles(stlFiles);
      state.uploadStorageStatus = "Saved locally in this browser. Registering STL bytes with the local engine...";
    } catch (error) {
      state.uploadStorageStatus = `Loaded for this session only; browser storage failed: ${error.message}`;
    }
    await registerUploadedStls(stlFiles);
  } else {
    await clearUploadedFiles().catch(() => {});
    state.uploadStorageStatus = files.length ? "No STL files were selected." : "";
    el("stlFile").value = "";
    el("simpleStlFile").value = "";
  }
  renderAll();
}

async function addCaseRecordFiles(files, forced = {}) {
  const usable = files.filter((file) => file?.name);
  if (!usable.length) return;
  state.recordUploadStatus = `Registering ${usable.length} case record(s) locally...`;
  renderAll();
  let added = 0;
  const errors = [];
  for (const file of usable) {
    const classified = classifyCaseRecord(file, forced);
    try {
      const result = await uploadCaseRecord(file, classified);
      if (result.ok === false) {
        errors.push(`${file.name}: ${(result.errors || ["record upload failed"]).join("; ")}`);
        continue;
      }
      upsertCaseRecord(result.record);
      added += 1;
    } catch (error) {
      errors.push(`${file.name}: ${error.message}`);
    }
  }
  updateAvailabilityFromCaseRecords();
  state.recordUploadStatus = added
    ? `Attached ${added} local case record(s).${errors.length ? ` ${errors.length} failed.` : ""}`
    : `No case records attached. ${errors.join("; ")}`;
  renderAll();
}

function classifyCaseRecord(file, forced = {}) {
  if (forced.kind) return forced;
  const name = String(file.name || "").toLowerCase();
  const type = String(file.type || "").toLowerCase();
  if (name.endsWith(".dcm") || name.endsWith(".dicom") || type.includes("dicom")) {
    return { kind: "dicom", modality: "DICOM" };
  }
  if (name.includes("xray") || name.includes("x-ray") || name.includes("radiograph") || name.includes("pano") || name.includes("ceph")) {
    return { kind: "radiograph", modality: "radiograph" };
  }
  if (type.startsWith("image/")) return { kind: "photo", modality: "photo" };
  return { kind: "document", modality: "document" };
}

function addNoteRecord() {
  const input = el("recordNote");
  const text = input.value.trim();
  if (!text) return;
  upsertCaseRecord({
    id: `note-${Date.now().toString(36)}`,
    kind: "note",
    modality: "note",
    filename: "review-note.txt",
    note_text: text,
    provenance: "manual",
    created_at: new Date().toISOString(),
  });
  input.value = "";
  state.recordUploadStatus = "Attached review note.";
  updateAvailabilityFromCaseRecords();
}

function upsertCaseRecord(record) {
  if (!record?.id) return;
  const index = state.caseRecords.findIndex((item) => item.id === record.id);
  if (index >= 0) {
    state.caseRecords[index] = record;
  } else {
    state.caseRecords.push(record);
  }
}

function updateAvailabilityFromCaseRecords() {
  const kinds = new Set(state.caseRecords.map((record) => record.kind));
  state.availability.cbct = kinds.has("cbct") || kinds.has("dicom");
  state.availability.photos = kinds.has("photo");
  state.availability.radiographs = kinds.has("radiograph");
  state.availability.clinician_notes = kinds.has("note");
}

// Reviewer accepts/corrects/rejects a CBCT-derived anatomy object. Mutates the
// review_status in place and re-evaluates; the engine recomputes the trusted
// flag and review tier (root/bone-aware stays fail-closed unless accepted).
const ANATOMY_GROUPS = { roots: "roots", tooth_axes: "tooth_axes", alveolar_bone: "alveolar_bone" };

async function applyAnatomyReview(group, index, status) {
  const key = ANATOMY_GROUPS[group];
  const list = key && state.derivedAnatomy ? state.derivedAnatomy[key] : null;
  if (!Array.isArray(list) || !list[index]) return;
  try {
    const result = await requestCbctAnatomyReview({
      plan: planJson(),
      decisions: [{ group: key, index, review_status: status }],
    });
    if (result.ok === false) {
      state.cbctWorkflow.status = (result.errors || ["Could not apply anatomy review."]).join("; ");
    } else {
      applyServerPlanParts(result.plan);
      state.cbctWorkflow.status = `Marked ${key} #${index + 1} ${status}.`;
    }
  } catch (error) {
    state.cbctWorkflow.status = error.message;
  }
  renderAll();
}

async function loadCbctMaskFile(file) {
  if (!file) return;
  try {
    const parsed = JSON.parse(await file.text());
    state.cbctWorkflow.mask = parsed;
    const rootCount = Object.keys(parsed.root_voxels_by_tooth || {}).length;
    const boneCount = Array.isArray(parsed.bone_voxels) ? parsed.bone_voxels.length : 0;
    state.cbctWorkflow.status = `Loaded ${file.name}: ${rootCount} root mask(s), ${boneCount} bone voxel(s).`;
  } catch (error) {
    state.cbctWorkflow.mask = null;
    state.cbctWorkflow.status = `Could not read mask JSON: ${error.message}`;
  }
  renderAll();
}

async function proposeCbctAnatomy() {
  const workflow = state.cbctWorkflow;
  if (workflow.busy || !workflow.mask) return;
  const cbct = state.caseRecords.find((record) => record.kind === "cbct" || record.kind === "dicom");
  const source = state.scanSources.find((item) => item.asset?.id);
  if (!cbct || !source?.asset?.id) {
    workflow.status = "Attach CBCT/DICOM and register an STL scan before importing masks.";
    renderAll();
    return;
  }
  workflow.busy = true;
  workflow.status = "Importing masks as proposed anatomy...";
  renderAll();
  try {
    const result = await requestCbctAnatomyProposal({
      plan: planJson(),
      cbct_record_id: cbct.id,
      source_stl_asset_id: source.asset.id,
      registration_accepted: workflow.registrationAccepted,
      registration_quality: {
        method: "local-review",
        rmse_mm: workflow.rmseMm,
        fitness: workflow.fitness,
      },
      mask: workflow.mask,
    });
    if (result.ok === false) {
      workflow.status = (result.errors || ["CBCT proposal import failed."]).join("; ");
    } else {
      applyServerPlanParts(result.plan);
      const roots = result.proposal?.roots?.length || 0;
      const axes = result.proposal?.tooth_axes?.length || 0;
      const bone = result.proposal?.alveolar_bone?.length || 0;
      workflow.status = `Proposed ${roots} root(s), ${axes} axis record(s), and ${bone} bone record(s). Review before trust.`;
    }
  } catch (error) {
    workflow.status = error.message;
  } finally {
    workflow.busy = false;
    renderAll();
  }
}

function applyServerPlanParts(snapshot) {
  if (!snapshot) return;
  state.registrations = snapshot.registrations || [];
  state.derivedAnatomy = snapshot.derived_anatomy || null;
}

async function registerUploadedStls(files) {
  const registered = [];
  const errors = [];
  for (const file of files) {
    try {
      const arch = state.scanArch || inferArchFromName(file.name) || "";
      const result = await uploadStlFile(file, { arch });
      if (result.ok === false) {
        errors.push(`${file.name}: ${(result.errors || ["upload failed"]).join("; ")}`);
        continue;
      }
      registered.push({
        name: file.name,
        url: result.url,
        arch: arch || inferArchFromName(file.name) || null,
        asset: result.asset,
      });
    } catch (error) {
      errors.push(`${file.name}: ${error.message}`);
    }
  }
  state.scanSources = registered;
  if (registered.length) {
    const detail = errors.length ? ` ${errors.length} upload(s) could not be registered.` : "";
    state.uploadStorageStatus =
      `Registered ${registered.length} STL file(s) with the local engine for segmentation and case metadata.${detail}`;
  } else if (errors.length) {
    state.uploadStorageStatus =
      `Loaded in this browser, but the local engine could not register the STL bytes: ${errors.join("; ")}`;
  }
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

// Build the mobile-handoff case review on the engine, download it, and show the
// deep link a device can scan/open. Mobile imports it read-only (edit-locked).
async function exportCaseReview() {
  const status = el("caseHandoffStatus");
  if (status) status.textContent = "Building case review...";
  try {
    const result = await requestCaseReview({ plan: planJson(), base_url: window.location.origin });
    if (result.ok === false) {
      if (status) status.textContent = (result.errors || ["case review failed"]).join("; ");
      return;
    }
    const review = result.review;
    downloadJson(`orthoplan-case-review-${safeDownloadToken(review.case_id || review.plan_id || "case")}.json`, review);
    if (status) {
      const tier = review.review_tier?.label || review.review_tier?.tier || "review";
      status.textContent = `Exported ${tier} (read-only on mobile). Open on a device: ${review.handoff.qr_payload}`;
    }
    renderCaseHandoff(review);
  } catch (error) {
    if (status) status.textContent = String(error.message || error);
  }
}

function safeDownloadToken(value) {
  return String(value || "case").replace(/[^A-Za-z0-9._-]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 80) || "case";
}

function renderCaseHandoff(review) {
  const target = el("caseHandoffQr");
  const payload = review?.handoff?.qr_payload;
  if (!target || !payload) return;
  try {
    target.innerHTML = qrSvg(payload);
  } catch (error) {
    const fallback = review?.handoff?.deep_link;
    if (!fallback || fallback === payload) {
      target.textContent = String(error.message || error);
      return;
    }
    target.innerHTML = qrSvg(fallback);
  }
  const label = document.createElement("p");
  label.className = "guided-hint";
  label.textContent = payload;
  target.appendChild(label);
}

// Apply one planar nudge to the selected tooth's authored target. `direction` is
// "x-" | "x+" | "y-" | "y+". Gated on confirmed scan units so a mm nudge is
// never authored against unverified scale. Movement itself is recomputed by the
// engine on the next evaluation (the UI never computes poses).
function pushManualUndo() {
  const stack = state.manualEdit.undoStack || [];
  stack.push(state.rows.map((row) => ({ ...row })));
  state.manualEdit.undoStack = stack.slice(-20);
}

function applyManualNudge(direction) {
  const tooth = state.manualEdit.selectedTooth;
  if (!tooth || !scaleConfirmed(state.scanUnits)) return;
  const axis = direction[0]; // "x" or "y"
  const delta = direction.endsWith("-") ? -NUDGE_STEP_MM : NUDGE_STEP_MM;
  pushManualUndo();
  state.rows = nudgeTarget(state.rows, tooth, axis, delta);
  renderAll();
}

function loadSyntheticDemo() {
  stopStagePlayback();
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
  el("scanUnits").value = "mm";
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
    state.uploadStorageStatus = "Restored saved STL files from this browser. Registering with the local engine...";
    await registerUploadedStls(files);
    updateUploadLabels();
    renderAll();
  } catch {
    // Browser storage is a convenience; a failed restore should never block use.
  }
}

async function toggleProximity() {
  const prox = state.proximity;
  if (prox.busy) return;
  // Already have an alignable map: the toggle just shows/hides the overlay.
  if (prox.map && prox.map.aligned_to_scan) {
    prox.enabled = !prox.enabled;
    renderAll();
    return;
  }
  // Otherwise fetch it (server registers the scan pair and classifies clearance).
  prox.status = "Registering the bite and mapping proximity on this machine...";
  renderAll();
  await requestProximity();
  // The proximity toggle owns the overlay's visibility: show it only when a fetch
  // produced a scan-aligned map (the registered-bite toggle reuses the same fetch
  // but must NOT switch the overlay on).
  prox.enabled = Boolean(prox.map && prox.map.aligned_to_scan);
  renderAll();
}

async function toggleRegisteredBite() {
  const prox = state.proximity;
  if (prox.busy) return;
  // The registered-bite view needs the registration, which comes from the same
  // server occlusion pass as the proximity overlay. Fetch it on first use.
  if (!prox.registration) {
    prox.status = "Registering the bite on this machine...";
    renderAll();
    await requestProximity();
  }
  if (registrationActionable(prox.registration)) {
    prox.registeredView = !prox.registeredView;
    prox.status = prox.registeredView
      ? "Registered bite applied: the lower arch is moved into an ESTIMATED occlusion (approximate alignment, not a measured bite)."
      : "Registered bite off: showing the arches at their scanned positions.";
  } else if (prox.registration) {
    // As-scanned exports already occlude, so there is nothing to move.
    prox.registeredView = false;
    prox.status =
      "These arches already occlude as scanned, so the viewer already shows the true bite — nothing to register.";
  }
  renderAll();
}

function toggleStagePlayback() {
  if (state.stagePlayback.playing) {
    stopStagePlayback();
    renderAll();
    return;
  }
  const slider = el("stageSlider");
  const max = Number(slider.max || 0);
  if (max <= 0) return;
  state.stagePlayback.playing = true;
  state.stagePlayback.timer = setInterval(() => {
    const current = Number(slider.value || 0);
    slider.value = String(current >= max ? 0 : current + 1);
    renderStagePreview();
  }, 750);
  renderAll();
}

function stopStagePlayback() {
  if (state.stagePlayback.timer) clearInterval(state.stagePlayback.timer);
  state.stagePlayback.timer = null;
  state.stagePlayback.playing = false;
}

async function sendChatMessage() {
  const message = state.chat.input.trim();
  if (!message || state.chat.busy) return;
  const history = state.chat.messages
    .filter((item) => item.role === "user" || item.role === "assistant")
    .slice(-16);
  state.chat.busy = true;
  state.chat.status = "Reviewing the scoped plan context...";
  state.chat.messages.push({ role: "user", content: message });
  state.chat.messages.push({ role: "assistant", content: "Reviewing the scoped plan context..." });
  el("chatInput").value = "";
  state.chat.input = "";
  renderChat();
  try {
    // The API key is read straight from the DOM at send time so it is never
    // held in app state or persisted - only transmitted on an explicit "Ask AI".
    const apiKey = el("chatApiKey").value.trim();
    const payload = {
      plan: planJson(),
      message,
      history,
      provider: state.chat.provider,
      model: state.chat.model,
      // The assistant always works from the full plan context (no scope selector).
      context_scope: state.chat.contextScope,
      ui_context: buildChatUiContext(),
      api_key: apiKey || undefined,
      endpoint: state.chat.agentEndpoint.trim() || undefined,
      share_acknowledged: state.chat.agentAccessEnabled,
      session_id: state.chat.sessionId || undefined,
    };
    const pending = state.chat.messages[state.chat.messages.length - 1];
    const connector = (state.chat.connectors || []).find((item) => item.kind === state.chat.provider);
    const result = connector?.supports_streaming
      ? await streamChatPayload(payload, pending)
      : await askPlanAssistant(payload);
    if (result.ok === false) {
      pending.content = (result.errors || ["AI chat is not available."]).join(" ");
      state.chat.status = "Connector unavailable";
    } else {
      const assistant = [...result.session.messages].reverse().find((item) => item.role === "assistant");
      pending.content = assistant?.content || "No answer returned.";
      state.chat.sessionId = result.session.session_id;
      state.chat.status = `${result.session.connector.label} · ${result.session.context_scope.name}`;
    }
  } catch (error) {
    const pending = state.chat.messages[state.chat.messages.length - 1];
    if (pending?.role === "assistant") pending.content = error.message;
    else state.chat.messages.push({ role: "assistant", content: error.message });
    state.chat.status = "Chat request failed";
  } finally {
    state.chat.busy = false;
    el("chatInput").focus();
    renderChat();
  }
}

async function streamChatPayload(payload, pending) {
  pending.content = "";
  let finalResult = null;
  await streamPlanAssistant(payload, {
    onDelta: (text) => {
      pending.content += text;
      renderChat();
    },
    onDone: (result) => {
      finalResult = result;
    },
  });
  return finalResult || { ok: false, errors: ["AI chat stream ended without a final response."] };
}

function defaultModelForProvider(provider) {
  const connector = (state.chat.connectors || []).find((item) => item.kind === provider);
  return connector?.model || connector?.models?.[0] || "local-educational-helper";
}

function buildChatUiContext() {
  const active = state.userMode === "simple"
    ? state.guided.step
    : state.activeStep;
  const stage = state.userMode === "simple"
    ? GUIDED_STAGE_CONTEXT[active] || GUIDED_STAGE_CONTEXT.upload
    : TECH_STAGE_CONTEXT[active] || TECH_STAGE_CONTEXT.upload;
  const evaluation = state.lastEval || {};
  return {
    mode: state.userMode === "simple" ? "Guided" : "Technician",
    active_step: active,
    label: stage.label,
    purpose: stage.purpose,
    plan_title: el("planTitle").value,
    plan_id: el("planId").value,
    scan_files: state.files.map((file) => file.name),
    scan_units: state.scanUnits,
    scan_arch: state.scanArch || "unknown",
    row_count: state.rows.length,
    stage_rows: state.rows,
    guided: {
      step: state.guided.step,
      excluded_teeth: state.guided.excludedTeeth,
      goal: state.simpleGoal,
      acknowledged: state.simpleAcknowledged,
      print_status: state.guided.print.status,
    },
    generation: {
      status: state.generation.status,
      source: state.generation.result?.source || null,
      has_landmarks: Boolean(state.generation.landmarks),
    },
    segmentation: {
      status: state.segmentation.status,
      proposed_count: state.segmentation.proposal?.teeth?.length || 0,
      applied_count: state.segmentation.applied?.tooth_meshes?.length || 0,
      missing_teeth: state.segmentation.missingTeeth,
    },
    current_evaluation: {
      finding_count: evaluation.findings?.length || 0,
      data_gaps: evaluation.data_gaps || [],
      acquisition_next: evaluation.acquisition?.items || [],
      timeline: evaluation.timeline || null,
    },
  };
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
  stopStagePlayback();
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
  state.caseRecords = snapshot.case_records || [];
  state.registrations = snapshot.registrations || [];
  state.derivedAnatomy = snapshot.derived_anatomy || null;
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

import { sampleAssetUrl, sampleDataset } from "./sample-dataset.js";
// Sample test case: isolated observed history plus a separately selected
// simulated planning walkthrough that reuses the guided wizard.
//
// Opening it snapshots the user's working state and restores it on exit, so
// nothing the sample does leaks into the user's own plan, uploads, or editors.
//
// The default view compares original baseline and week 7 observations. The
// separately selected planning simulation can prepare an auto-segmented draft;
// its staged movements must never be presented as this person's observed history.

import { isolateSampleSettings } from "./sample_settings.js";
import { el, state } from "./state.js";
import { canonicalScanSources, demoInitialOffsets, syntheticCrowdingRows } from "./demo.js";

// State keys the sample overwrites and therefore must save/restore.
const SNAPSHOT_STATE_KEYS = [
  "rows", "files", "file", "scanDates", "scanSources", "caseRecords", "fixtureMeshAssets", "registrations", "derivedAnatomy",
  "recordUploadStatus", "useDemoMeshes", "demoInitialOffsets",
  "scanUnits", "view", "activeStep", "userMode", "scanArchFilter", "simpleGoal",
  "simpleAcknowledged", "dim", "sampleStatus", "scanRenderStatus", "availability",
];

const ROOT_BONE_FIXTURE_URL = sampleAssetUrl("fixtures/root-bone-fixture.json");
// DOM field values the sample overwrites and must restore.
const SNAPSHOT_FIELDS = ["planTitle", "planId", "wearInterval", "exaggeration", "scanUnits", "scanArch", "simpleGoal"];

let saved = null;

export function sampleActive() {
  return Boolean(saved);
}

export function enterSample() {
  if (saved) return;
  saved = {
    state: {},
    fields: {},
    acknowledged: el("simpleAcknowledged").checked,
    guidedStep: state.guided.step,
    excludedTeeth: [...state.guided.excludedTeeth],
    // segmentation is a nested object mutated in place, so snapshot the whole
    // object and give the sample a fresh one - otherwise a segmentation applied
    // inside the sample would leak into the user's real plan on exit.
    segmentation: state.segmentation,
    // Proximity is likewise a nested, scan-specific object; snapshot it and give the
    // sample a fresh one so a bite overlay computed inside the sample never leaks.
    proximity: state.proximity,
    manualEdit: state.manualEdit,
  };
  for (const key of SNAPSHOT_STATE_KEYS) saved.state[key] = state[key];
  for (const field of SNAPSHOT_FIELDS) saved.fields[field] = el(field).value;
  saved.restoreSettings = isolateSampleSettings();
  state.segmentation = { busy: false, status: "", proposal: null, edits: {}, applied: null };
  state.proximity = { enabled: false, busy: false, status: "", map: null, registration: null, registeredView: false };
  state.manualEdit = { selectedTooth: null, status: "", undoStack: [] };
  // Fresh data manifest for the sample plan (the user's object is snapshotted
  // above and restored on exit): only the bundled intraoral scans are "available"
  // until the sample's segmentation is applied (prepareSampleSegmentation).
  state.availability = {
    ...state.availability,
    intraoral_scan: true, segmented_teeth: false, roots: false, cbct: false,
    periodontal_status: false, occlusion_scan: false, photos: false,
    radiographs: false, clinician_notes: false,
  };

  // Isolated walkthrough plan: a simulated crowding correction over 4 stages
  // (0 = the starting point), paired with the two real test-case STL scans so the
  // 3D preview renders the exact bundled models, not bundled placeholder crowns.
  state.rows = syntheticCrowdingRows(4, { includeBaseline: true });
  state.demoInitialOffsets = demoInitialOffsets;
  state.useDemoMeshes = false;
  state.scanSources = canonicalScanSources;
  state.caseRecords = [];
  state.fixtureMeshAssets = [];
  state.registrations = [];
  state.derivedAnatomy = null;
  state.recordUploadStatus = "";
  state.files = [];
  state.file = null;
  state.scanArchFilter = "both";
  state.view = "overlay";
  state.dim = "3d";
  state.simpleGoal = "crowding";
  // Every tooth in the plan is included (none held still) so step 2 reads as
  // "all teeth selected".
  state.guided.excludedTeeth = [];
  // Reuse the guided wizard (not a separate screen) so the sample shows the same
  // step chips and panels; the sample flag drives the banner and isolation.
  state.userMode = "simple";
  state.sample.active = true;
  state.sample.view = "observed";
  state.sample.visit = "progress-01";
  // Open directly on the shared scan selection and stage viewer.
  state.guided.step = "plan";
  state.activeStep = "review";
  state.simpleAcknowledged = true;
  state.sampleStatus = "Week 1–18 scan history. The planning simulation is a separate example.";
  el("planTitle").value = `Sample test case · ${sampleDataset.pseudonym}`;
  el("planId").value = "sample-test-case";
  el("simpleGoal").value = "crowding";
  el("wearInterval").value = "7";
  el("exaggeration").value = "1";
  el("scanUnits").value = "mm";
  el("simpleAcknowledged").checked = true;
}

export async function applySampleRootBoneFixture() {
  if (!state.sample.active) return false;
  const session = state.segmentation;
  try {
    const response = await fetch(ROOT_BONE_FIXTURE_URL);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const fixture = await response.json();
    if (!state.sample.active || state.segmentation !== session) return false;
    state.caseRecords = fixture.case_records || [];
    state.fixtureMeshAssets = fixture.mesh_assets || [];
    state.registrations = fixture.registrations || [];
    state.derivedAnatomy = fixture.derived_anatomy || null;
    state.availability = { ...state.availability, ...(fixture.availability_patch || {}) };
    state.recordUploadStatus =
      "Sample root/bone fixture loaded: redacted CBCT metadata, accepted fixture registration, and safe derived landmarks.";
    return true;
  } catch (error) {
    if (!state.sample.active || state.segmentation !== session) return false;
    state.recordUploadStatus = `Sample root/bone fixture unavailable: ${error.message}`;
    return false;
  }
}

// Painted regions are selectable drafts. Loading them never records user review.
export async function prepareSampleSegmentation({ visit = state.sample.visit || "progress-01", allowFallback = false } = {}) {
  if (!state.sample.active) return false;
  const seg = state.segmentation;
  if (seg.busy) return false;
  seg.busy = true;
  seg.status = "Loading saved USER_ONE tooth regions…";
  try {
    const response = await fetch("/api/sample-teeth", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ visit, allow_baseline_fallback: allowFallback }) });
    const result = await response.json();
    if (!state.sample.active || state.segmentation !== seg) return false;
    if (!response.ok || !result.ok) throw new Error((result.errors || ["Painted regions unavailable"]).join(" "));
    state.sample.visit = result.visit || visit; state.goalPreview = null;
    state.scanSources = result.scan_sources;
    state.scanUnits = result.scan_sources.every(source => source.asset.units === "mm") ? "mm" : "unverified";
    el("scanUnits").value = state.scanUnits;
    seg.applied = result.plan_fragment;
    seg.annotations = result.annotations;
    seg.proposal = null;
    // Start from the observation, with no invented default movement.
    const teeth = result.plan_fragment.tooth_meshes.map(link => link.tooth.value);
    state.rows = Array.from({ length: 4 }, (_, stage) => teeth.map(tooth =>
      ({ stage, tooth, x: 0, y: 0, z: 0, tip: 0, torque: 0, rotation: 0 }))).flat();
    state.demoInitialOffsets = {}; state.manualEdit = { selectedTooth: teeth[0] || null, status: "", undoStack: [] };
    state.availability = { ...state.availability, segmented_teeth: false };
    state.caseRecords = []; state.fixtureMeshAssets = []; state.registrations = []; state.derivedAnatomy = null;
    state.availability = { ...state.availability, cbct: false, roots: false };
    state.view = "current"; state.activeStep = "review";
    el("stageSlider").value = "0";
    seg.status = `USER_ONE week ${state.sample.visit === "initial" ? 1 : 7}: saved painted regions loaded as drafts. Review a selected region before proposing movement.`;
    state.sampleStatus = (result.notice ? `${result.notice} ` : "") + "Sample ready. Choose any painted tooth by FDI or US number. Rotate or pan to inspect it. The stage slider starts with zero movement.";
    return true;
  } catch (error) {
    if (state.sample.active && state.segmentation === seg) { seg.status = error.message; state.sampleStatus = error.message; }
    return false;
  } finally { seg.busy = false; }
}

export function exitSample() {
  if (!saved) return;
  for (const key of SNAPSHOT_STATE_KEYS) state[key] = saved.state[key];
  for (const field of SNAPSHOT_FIELDS) el(field).value = saved.fields[field];
  el("simpleAcknowledged").checked = saved.acknowledged;
  state.guided.step = saved.guidedStep;
  state.guided.excludedTeeth = saved.excludedTeeth;
  state.segmentation = saved.segmentation;
  state.proximity = saved.proximity;
  state.manualEdit = saved.manualEdit;
  state.sample.active = false;
  saved.restoreSettings();
  saved = null;
}
